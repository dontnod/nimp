// Compile with: g++ -std=c++11 nimp-run.cpp -o nimp-run.exe

#include <windows.h>
#include <vector>
#include <string>

#include <cstdio>
#include <unistd.h>

int main(int argc, char *argv[])
{
    if (argc < 2)
    {
        printf("nimp-run: too few arguments.\n");
        return EXIT_FAILURE;
    }

    std::string arglist;
    for (int i = 1; i < argc; ++i, arglist += ' ')
    {
        if (strchr(argv[i], ' '))
        {
            arglist += '"';
            arglist += argv[i];
            arglist += '"';
        }
        else
        {
            arglist += argv[i];
        }
    }

    char cwd[MAX_PATH] = { 0 };
    getcwd(cwd, MAX_PATH);

    printf("nimp-run: executing %s [in %s]\n", argv[1], arglist.c_str(), cwd);

    PROCESS_INFORMATION pi = { 0 };
    STARTUPINFO si = { 0 };
    if (!CreateProcess(nullptr, &arglist[0], nullptr, nullptr,
                       FALSE, DEBUG_ONLY_THIS_PROCESS,
                       nullptr, nullptr, &si, &pi))
    {
        printf("nimp-run: cannot CreateProcess(%s): 0x%l08x\n", argv[1], GetLastError());
        return EXIT_FAILURE;
    }

    DebugActiveProcess(pi.dwProcessId);

    std::vector<char> data;
    int cygwin_startup_skip = 2;

    for (;;)
    {
        DEBUG_EVENT de;

        if (!WaitForDebugEvent(&de, INFINITE))
        {
            printf("nimp-run: cannot WaitForDebugEvent(): 0x%l08x\n", GetLastError());
            return EXIT_FAILURE;
        }

        if (de.dwDebugEventCode == EXIT_PROCESS_DEBUG_EVENT)
        {
            break;
        }

        if (de.dwDebugEventCode == OUTPUT_DEBUG_STRING_EVENT)
        {
            data.resize(de.u.DebugString.nDebugStringLength);
            ReadProcessMemory(pi.hProcess, de.u.DebugString.lpDebugStringData,
                              data.data(), data.size(), nullptr);

            if (cygwin_startup_skip && data.size() >= 3
                 && data[0] == 'c' && data[1] == 'Y' && data[2] == 'g')
            {
                --cygwin_startup_skip;
            }
            else
            {
                fwrite(data.data(), data.size(), 1, stdout);
            }
        }

        ContinueDebugEvent(de.dwProcessId, de.dwThreadId, DBG_CONTINUE);
    }

    DWORD exit_code;
    GetExitCodeProcess(pi.hProcess, &exit_code);

    printf("nimp-run: process exited with status %d (0x%08x)\n",
           (int)exit_code, (int)exit_code);

    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return exit_code ? EXIT_FAILURE : EXIT_SUCCESS;
}

