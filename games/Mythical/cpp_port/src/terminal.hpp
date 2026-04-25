#pragma once

namespace mythical::port {

// Clear the terminal screen on the current platform.
void clear_screen();

// Read a single key (blocking). Returns the keycode (ASCII where possible).
// Falls back to reading a line and taking the first non-whitespace char if
// raw input is unavailable.
int read_key();

}  // namespace mythical::port
