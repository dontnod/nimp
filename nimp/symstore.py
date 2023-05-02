# -*- coding: utf-8 -*-
# Copyright (c) 2014-2023 Dontnod Entertainment

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

''' SymStore abstraction '''

import contextlib
import logging
import os
from pathlib import Path
import tempfile
from typing import Optional

import nimp.sys.platform
import nimp.system
import nimp.sys.process


class SymStore:

    @staticmethod
    def get_symstore(env) -> Optional['SymStore']:
        if env.is_win64 or env.is_xsx:
            return MSFTSymStore()
        elif env.is_ps5:
            return PS5SymStore()
        else:
            logging.error("Plafrom must be win64, xsx or ps5")
            return None

    @staticmethod
    @contextlib.contextmanager
    def rsp_file(symbols: list[os.PathLike]):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as symbols_index:
            index_file = Path(symbols_index.name)
            for symbol in symbols:
                logging.debug("adding %s to response file %s", symbol, index_file)
                symbols_index.write(f"{symbol}\n")

        try:
            yield index_file
        finally:
            nimp.system.try_remove(str(index_file), dry_run=False)

    @staticmethod
    def get_symstore_tool_path() -> Optional[Path]:
        raise NotImplementedError('get_symstore_tool_path')

    @staticmethod
    def upload_symbols(symbols: list[os.PathLike], store_path: os.PathLike, compress: bool = False, dry_run: bool = False, **kwargs):
        raise NotImplementedError('upload_symbols')


def get_autosdk_for_platform(platform) -> Optional[Path]:
    # Only supported on Windows at the moment
    assert nimp.sys.platform.is_windows()

    autosdk_root = os.getenv('UE_SDKS_ROOT')
    if autosdk_root is None:
        return None

    platform_autosdk_root: Path = Path(autosdk_root) / 'HostWin64' / platform
    if not platform_autosdk_root.exists():
        return None

    return platform_autosdk_root


class MSFTSymStore(SymStore):
    @staticmethod
    def get_symstore_tool_path() -> Optional[Path]:
        symstore_subpath_in_sdk = 'Windows Kits/10/Debuggers/x64/symstore.exe'

        win64_autosdk = get_autosdk_for_platform('Win64')
        if win64_autosdk is not None:
            symstore_candidate = win64_autosdk / symstore_subpath_in_sdk
            if symstore_candidate.exists():
                # Direct return, always prefer the symstore in autoSDK
                return symstore_candidate

        symstore_candidate = Path("C:/Program Files (x86)/Windows Kits/10/Debuggers/x64/symstore.exe")
        if symstore_candidate.exists():
            return symstore_candidate

        return None

    # Approx. 2GB
    CAB_SRC_SIZE_LIMIT = 1.5 * 1000 * 1000 * 1000

    @staticmethod
    def upload_symbols(symbols: list[os.PathLike], store_path: os.PathLike, product_name: str = None, comment: str = None, version: str = None, compress: bool = False, use_index2: bool = True, dry_run: bool = False, **kwargs) -> bool:
        # in case we are given a generator
        symbols = list(symbols)
        if len(symbols) <= 0:
            logging.info('No symbols were provided')
            return True

        symstore_exe = MSFTSymStore.get_symstore_tool_path()
        if symstore_exe is None:
            raise FileNotFoundError('Failed to find a valid symstore executable')

        symstore_common_args: list[str] = [
            str(symstore_exe),
            'add',
            "/r",  # Recursive
            "/s", store_path,  # target symbol store
            "/o",  # Verbose output
            "-:NOFORCECOPY",  # no documentation on this but seems to not override files already in store
        ]
        if use_index2:
            symstore_common_args.append("/3")
        if product_name is not None:
            symstore_common_args.extend(['/t', product_name])
        if comment is not None:
            symstore_common_args.extend(['/c', comment])
        if version is not None:
            symstore_common_args.extend(['/v', version])

        symbols_with_args: list[tuple[list[str], list[os.PathLike]]] = []
        if compress:
            # Microsoft symstore.exe uses CAB compression  which has a hard limit on source file size of 2GB.
            # Switch to ZIP compression if a file exceed this limit to prevent corrupted archives
            # (benefits are faster compression time and handle file size > 2GB but compress less)
            default_compression_symbols = []
            zip_compression_symbols = []
            for sym in symbols:
                if os.path.exists(sym):
                    if os.path.getsize(sym) >= MSFTSymStore.CAB_SRC_SIZE_LIMIT:
                        zip_compression_symbols.append(sym)
                    else:
                        default_compression_symbols.append(sym)

            if len(default_compression_symbols) > 0:
                symbols_with_args.append((['/compress'], default_compression_symbols))
            if len(zip_compression_symbols) > 0:
                symbols_with_args.append((['/compress', 'ZIP'], zip_compression_symbols))
        else:
            # No compression, pretty straightforward
            symbols_with_args.append(([], symbols))

        success = True
        for additional_args, symbols in symbols_with_args:
            with SymStore.rsp_file(symbols) as rsp_filepath:
                commandline = list(symstore_common_args) + [
                    '/f', f'@{rsp_filepath}',
                ] + additional_args

                return_code = nimp.sys.process.call(commandline, dry_run=dry_run)
                if return_code != 0:
                    logging.error('Failed to generate IndexFile (error code: %d)', return_code)
                    success = False

        return success


class PS5SymStore(SymStore):

    @staticmethod
    def get_symstore_tool_path() -> Optional[Path]:
        symupload_candidates: list[Path] = []
        symupload_subpath_in_sdk = 'NotForLicensees/*/host_tools/bin/prospero-symupload.exe'

        ps5_autosdk = get_autosdk_for_platform('PS5')
        if ps5_autosdk is not None:
            symupload_candidates.extend(ps5_autosdk.glob("*/" + symupload_subpath_in_sdk))

        prospero_sdk_root = os.getenv('SCE_PROSPERO_SDK_DIR')
        if prospero_sdk_root is not None:
            symupload_candidates.extend(Path(prospero_sdk_root).glob(symupload_subpath_in_sdk))

        def _ps5_sdk_version(p: Path):
            # path format is {ROOT_PATH}/{SDK_VERSION}/NotForLicensees/{SDK_SIMPLE}/host_tools/bin/prospero-symupload.exe
            # get the first {SDK_VERSION} as it is more detailed in autoSDK
            sdk_version_string = p.parents[4].name

            # SDK format is something of a mess
            # 1.000
            # 2.00.00.09
            # 2.000.009
            return tuple((int(e) if e.isdigit() else 0) for e in sdk_version_string.split('.'))

        symupload_candidates.sort(key=_ps5_sdk_version, reverse=True)

        if len(symupload_candidates) <= 0:
            return None
        return symupload_candidates[0]

    @staticmethod
    def upload_symbols(symbols: list[os.PathLike], store_path: os.PathLike, tag: str = None, compress: bool = False, dry_run: bool = False, **kwargs) -> bool:
        symstore_exe = PS5SymStore.get_symstore_tool_path()
        if symstore_exe is None:
            raise FileNotFoundError('Failed to find a valid symstore executable')

        with SymStore.rsp_file(symbols) as rsp_filepath:
            commandline = [
                str(symstore_exe),
                'add',
                '/r', '/f', f'@{rsp_filepath}',
                '/s', str(store_path),
                '/o',
            ]
            if tag is not None:
                commandline.extend(['/tag', tag])
            if compress:
                commandline.append('/compress')

            success = (nimp.sys.process.call(commandline, dry_run=dry_run) == 0)
            return success
