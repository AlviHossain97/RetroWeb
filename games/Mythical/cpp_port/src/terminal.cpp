#include "terminal.hpp"

#include <cstdio>
#include <iostream>
#include <string>

#if defined(_WIN32)
#include <conio.h>
#include <windows.h>
#else
#include <termios.h>
#include <unistd.h>
#endif

namespace mythical::port {

void clear_screen() {
#if defined(_WIN32)
    // ANSI escape works on modern Windows 10+ consoles; fall back to cls command.
    HANDLE h = GetStdHandle(STD_OUTPUT_HANDLE);
    DWORD mode = 0;
    if (GetConsoleMode(h, &mode)) {
        SetConsoleMode(h, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
    }
#endif
    std::cout << "\x1b[2J\x1b[H" << std::flush;
}

int read_key() {
#if defined(_WIN32)
    int ch = _getch();
    if (ch == 0 || ch == 0xE0) {
        // Extended key (arrows): consume second byte and map to WASD.
        int ext = _getch();
        switch (ext) {
            case 72: return 'w';  // up
            case 80: return 's';  // down
            case 75: return 'a';  // left
            case 77: return 'd';  // right
            default: return ext;
        }
    }
    return ch;
#else
    termios old{};
    if (tcgetattr(STDIN_FILENO, &old) != 0) {
        // Fallback: line-buffered.
        std::string line;
        if (!std::getline(std::cin, line)) return -1;
        for (char c : line) if (c != ' ' && c != '\t') return static_cast<unsigned char>(c);
        return '\n';
    }
    termios raw = old;
    raw.c_lflag &= ~(ICANON | ECHO);
    tcsetattr(STDIN_FILENO, TCSANOW, &raw);
    int ch = std::getchar();
    tcsetattr(STDIN_FILENO, TCSANOW, &old);
    return ch;
#endif
}

}  // namespace mythical::port
