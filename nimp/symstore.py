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

'''SymStore abstraction'''

import concurrent.futures
import contextlib
import datetime
import gzip
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

import nimp.build
import nimp.sys.platform
import nimp.sys.process
import nimp.system


class SymStore:
    @staticmethod
    def get_symstore(env) -> Optional['SymStore']:
        if env.is_win64 or env.is_xsx or env.is_wingdk:
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
    def upload_symbols(
        symbols: list[os.PathLike], store_path: os.PathLike, compress: bool = False, dry_run: bool = False, **kwargs
    ):
        raise NotImplementedError('upload_symbols')

    @staticmethod
    def cleanup_symbols(store_path: os.PathLike, keep_newer_than: datetime.date, dry_run: bool = False) -> bool:
        raise NotImplementedError('cleanup_symbols')


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

    @staticmethod
    def get_common_parent_path(paths: list[Path]) -> Path:
        common_parent = paths[0].parent
        for path in paths[1:]:
            common_parts = common_parent.parts
            path_parts = path.parts
            for idx in range(min(len(common_parts), len(path_parts))):
                if common_parts[idx] != path_parts[idx]:
                    common_parent = Path(*common_parts[:idx])
                    break

        return common_parent

    @staticmethod
    def gzip_compress_symbols(
        symbols: list[Path], dest_dir: Path, symbols_common_path: Optional[Path] = None
    ) -> list[Path]:
        if symbols_common_path is None:
            symbols_common_path = MSFTSymStore.get_common_parent_path(symbols)

        max_workers = os.cpu_count()
        if max_workers is not None:
            # Leave one thread idle to not saturate the CPU
            max_workers -= 1

        def _gzip_compress_fn(symbol: Path):
            tmp_sym: Path = dest_dir / symbol.relative_to(symbols_common_path)
            tmp_sym.parent.mkdir(parents=True, exist_ok=True)

            logging.info('GZIP compress %s to %s', symbol, tmp_sym)
            with gzip.open(tmp_sym, 'wb', compresslevel=9) as c_fp, symbol.open('rb') as o_fp:
                shutil.copyfileobj(o_fp, c_fp)

            return tmp_sym

        with concurrent.futures.ThreadPoolExecutor(
            thread_name_prefix='nimp_symbols_gzip_compress_', max_workers=max_workers
        ) as pool:
            return list(pool.map(_gzip_compress_fn, symbols))

    # Approx. 2GB
    CAB_SRC_SIZE_LIMIT = 2 * 1000 * 1000 * 1000

    @staticmethod
    def upload_symbols(  # ignore: type[override]
        symbols: list[os.PathLike],
        store_path: os.PathLike,
        product_name: str = None,
        comment: str = None,
        version: str = None,
        compress: bool = False,
        use_index2: bool = True,
        gzip_compress: bool = False,
        dry_run: bool = False,
        **kwargs,
    ) -> bool:
        if gzip_compress:
            compress = True

        # in case we are given a generator
        symbols = list(symbols)
        if len(symbols) <= 0:
            logging.info('No symbols were provided')
            return True
        symbols: list[Path] = [Path(s).resolve().absolute() for s in symbols]

        symstore_exe = MSFTSymStore.get_symstore_tool_path()
        if symstore_exe is None:
            raise FileNotFoundError('Failed to find a valid symstore executable')

        # Microsoft symstore.exe uses CAB compression  which has a hard limit on source file size of 2GB.
        if compress and not gzip_compress:
            if any(os.path.exists(sym) and os.path.getsize(sym) >= MSFTSymStore.CAB_SRC_SIZE_LIMIT for sym in symbols):
                raise RuntimeError(
                    'Some symbols are larger than CAB limit. Abort to prevent uploading corrupted symbols.'
                )

        symstore_common_args = [
            str(symstore_exe),
            'add',
            '/o',
        ]
        if use_index2:
            symstore_common_args.append("/3")

        common_parent = MSFTSymStore.get_common_parent_path(symbols)

        with tempfile.TemporaryDirectory(dir=common_parent) as tmp_dir:
            tmp_dir: Path = Path(tmp_dir)

            # Create index file for later add
            index_filepath = str(tmp_dir / 'index.txt')
            with SymStore.rsp_file(symbols) as rsp_filepath:
                commandline = list(symstore_common_args) + [
                    '/r',
                    '/f',
                    f'@{rsp_filepath}',
                    '/x',
                    index_filepath,
                    '/g',
                    str(common_parent),
                    '/o',
                ]

                return_code = nimp.sys.process.call(commandline, dry_run=dry_run)
                if return_code != 0:
                    logging.error('Failed to generate IndexFile (error code: %d)', return_code)
                    return False

            if gzip_compress and not dry_run:
                tmp_common_parent = Path(tmp_dir) / 'compressed_symbols'
                tmp_common_parent.mkdir(parents=True, exist_ok=True)

                symbols = MSFTSymStore.gzip_compress_symbols(symbols, tmp_common_parent, common_parent)
                common_parent = tmp_common_parent

            commandline = list(symstore_common_args) + [
                '-:NOFORCECOPY',  # no documentation on this but seems to not override files already in store
                '/y',
                index_filepath,
                '/g',
                str(common_parent),
                '/s',
                store_path,
            ]
            if compress and not gzip_compress:
                commandline.append('/compress')
            if comment is not None:
                commandline.extend(['/c', comment])
            if product_name is not None:
                commandline.extend(['/t', product_name])
            if version is not None:
                commandline.extend(['/v', version])

            def _try_execute_symstore(
                command: list[str, ...], max_attempts: int = 3, delay: int = 5, dry_run: bool = False
            ) -> int:
                """retry in case of error 32 or 80, to try and work around possible network issues
                This is a crappy solution that cannot replace making symbol servers reliable"""
                result: int = 0
                for attempt in range(max_attempts):
                    result = nimp.sys.process.call(command, dry_run=dry_run)
                    if result in [32, 80]:
                        logging.warn('There is a network error.')
                        logging.warn('Retrying : attempt %s out of %s...' % (attempt + 1, max_attempts))
                        time.sleep(delay)
                    else:
                        break

                return result

            return _try_execute_symstore(commandline, dry_run=dry_run) == 0

    @staticmethod
    def cleanup_symbols(store_path: os.PathLike, keep_newer_than: datetime.date, dry_run: bool = False) -> bool:
        logging.info("Clean symstore %s (%s)", store_path, keep_newer_than)
        transactions = nimp.build.get_symbol_transactions(store_path)
        if transactions is None:
            logging.error("Failed to retrieve symbol transactions for %s", store_path)
            return False

        symstore_exe = MSFTSymStore.get_symstore_tool_path()
        if symstore_exe is None:
            raise FileNotFoundError('Failed to find a valid symstore executable')

        success = True
        for transaction in transactions:
            transaction_date = datetime.datetime.strptime(transaction['creation_date'], '%m/%d/%Y').date()
            if transaction_date >= keep_newer_than:
                continue

            command = [str(symstore_exe), "del", "/s", str(store_path), "/i", transaction['id']]
            logging.info("Delete transaction %s from %s (date: %s)", transaction['id'], store_path, transaction_date)
            if nimp.sys.process.call(command, dry_run=dry_run) != 0:
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
    def upload_symbols(
        symbols: list[os.PathLike],
        store_path: os.PathLike,
        tag: str = None,
        compress: bool = False,
        dry_run: bool = False,
        **kwargs,
    ) -> bool:
        symstore_exe = PS5SymStore.get_symstore_tool_path()
        if symstore_exe is None:
            raise FileNotFoundError('Failed to find a valid symstore executable')

        with SymStore.rsp_file(symbols) as rsp_filepath:
            commandline = [
                str(symstore_exe),
                'add',
                '/r',
                '/f',
                f'@{rsp_filepath}',
                '/s',
                str(store_path),
                '/o',
            ]
            if tag is not None:
                commandline.extend(['/tag', tag])
            if compress:
                commandline.append('/compress')

            success = nimp.sys.process.call(commandline, dry_run=dry_run) == 0
            return success

    @staticmethod
    def cleanup_symbols(store_path: os.PathLike, keep_newer_than: datetime.date, dry_run: bool = False) -> bool:
        symstore_exe = PS5SymStore.get_symstore_tool_path()
        if symstore_exe is None:
            raise FileNotFoundError('Failed to find a valid symstore executable')

        logging.info("Clean symstore %s (%s)", store_path, keep_newer_than)

        command = [
            str(symstore_exe),
            "cleanup",
            '/s',
            str(store_path),
            '/force',
            '/before',
            f"{keep_newer_than} 00:00:00",
        ]
        if dry_run:
            command.append('/preview')

        return nimp.sys.process.call(command) == 0
