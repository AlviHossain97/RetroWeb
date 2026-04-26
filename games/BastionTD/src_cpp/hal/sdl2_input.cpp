#include "hal/sdl2_input.h"

#include <cstring>

namespace {

int scancode_to_button(SDL_Scancode sc) {
    switch (sc) {
        case SDL_SCANCODE_UP:
        case SDL_SCANCODE_W:        return static_cast<int>(InputButton::Up);
        case SDL_SCANCODE_DOWN:
        case SDL_SCANCODE_S:        return static_cast<int>(InputButton::Down);
        case SDL_SCANCODE_LEFT:
        case SDL_SCANCODE_A:        return static_cast<int>(InputButton::Left);
        case SDL_SCANCODE_RIGHT:
        case SDL_SCANCODE_D:        return static_cast<int>(InputButton::Right);
        case SDL_SCANCODE_Z:
        case SDL_SCANCODE_RETURN:   return static_cast<int>(InputButton::A);
        case SDL_SCANCODE_X:        return static_cast<int>(InputButton::B);
        case SDL_SCANCODE_Q:        return static_cast<int>(InputButton::L);
        case SDL_SCANCODE_E:        return static_cast<int>(InputButton::R);
        case SDL_SCANCODE_ESCAPE:
        case SDL_SCANCODE_BACKSPACE:return static_cast<int>(InputButton::Start);
        case SDL_SCANCODE_LSHIFT:
        case SDL_SCANCODE_RSHIFT:   return static_cast<int>(InputButton::Select);
        case SDL_SCANCODE_F:        return static_cast<int>(InputButton::FleetUpgrade);
        default:                    return -1;
    }
}

// Xbox-style gamepad button -> GBA-style InputButton. The mapping mirrors the
// keyboard layout so menu/gameplay feel identical on a pad.
int controller_button_to_button(SDL_GameControllerButton btn) {
    switch (btn) {
        case SDL_CONTROLLER_BUTTON_DPAD_UP:       return static_cast<int>(InputButton::Up);
        case SDL_CONTROLLER_BUTTON_DPAD_DOWN:     return static_cast<int>(InputButton::Down);
        case SDL_CONTROLLER_BUTTON_DPAD_LEFT:     return static_cast<int>(InputButton::Left);
        case SDL_CONTROLLER_BUTTON_DPAD_RIGHT:    return static_cast<int>(InputButton::Right);
        case SDL_CONTROLLER_BUTTON_A:             return static_cast<int>(InputButton::A);
        case SDL_CONTROLLER_BUTTON_B:             return static_cast<int>(InputButton::B);
        case SDL_CONTROLLER_BUTTON_Y:             return static_cast<int>(InputButton::FleetUpgrade);
        case SDL_CONTROLLER_BUTTON_X:             return static_cast<int>(InputButton::FastForward);
        case SDL_CONTROLLER_BUTTON_LEFTSHOULDER:  return static_cast<int>(InputButton::L);
        case SDL_CONTROLLER_BUTTON_RIGHTSHOULDER: return static_cast<int>(InputButton::R);
        case SDL_CONTROLLER_BUTTON_START:         return static_cast<int>(InputButton::Start);
        case SDL_CONTROLLER_BUTTON_BACK:          return static_cast<int>(InputButton::Select);
        default:                                  return -1;
    }
}

constexpr Sint16 kAxisDeadzone = 12000;
constexpr Sint16 kTriggerPressThreshold = 12000;

} // namespace

void SDL2Input::update() {
    // Lazily initialize controller subsystem + hot-plug the first detected pad.
    if (controller == nullptr) {
        if ((SDL_WasInit(SDL_INIT_GAMECONTROLLER) & SDL_INIT_GAMECONTROLLER) == 0) {
            SDL_InitSubSystem(SDL_INIT_GAMECONTROLLER);
        }
        for (int i = 0; i < SDL_NumJoysticks(); ++i) {
            if (SDL_IsGameController(i)) {
                controller = SDL_GameControllerOpen(i);
                if (controller != nullptr) {
                    break;
                }
            }
        }
    }

    SDL_Event ev;
    while (SDL_PollEvent(&ev)) {
        if (ev.type == SDL_QUIT) {
            quit = true;
        } else if (ev.type == SDL_KEYDOWN && ev.key.repeat == 0) {
            int btn = scancode_to_button(ev.key.keysym.scancode);
            if (btn >= 0) {
                pending_press[btn] = true;
            }
        } else if (ev.type == SDL_KEYUP) {
            int btn = scancode_to_button(ev.key.keysym.scancode);
            if (btn >= 0) {
                pending_release[btn] = true;
            }
        } else if (ev.type == SDL_CONTROLLERDEVICEADDED) {
            if (controller == nullptr && SDL_IsGameController(ev.cdevice.which)) {
                controller = SDL_GameControllerOpen(ev.cdevice.which);
            }
        } else if (ev.type == SDL_CONTROLLERDEVICEREMOVED) {
            if (controller != nullptr) {
                SDL_GameControllerClose(controller);
                controller = nullptr;
            }
        } else if (ev.type == SDL_CONTROLLERBUTTONDOWN) {
            int btn = controller_button_to_button(
                static_cast<SDL_GameControllerButton>(ev.cbutton.button));
            if (btn >= 0) {
                pending_press[btn] = true;
            }
        } else if (ev.type == SDL_CONTROLLERBUTTONUP) {
            int btn = controller_button_to_button(
                static_cast<SDL_GameControllerButton>(ev.cbutton.button));
            if (btn >= 0) {
                pending_release[btn] = true;
            }
        }
    }
}

void SDL2Input::advance_frame() {
    std::memcpy(prev, cur, sizeof(cur));

    const Uint8* keys = SDL_GetKeyboardState(nullptr);
    auto is_down = [&](SDL_Scancode primary, SDL_Scancode secondary = SDL_SCANCODE_UNKNOWN) {
        return keys[primary] || (secondary != SDL_SCANCODE_UNKNOWN && keys[secondary]);
    };

    cur[static_cast<int>(InputButton::Up)]           = is_down(SDL_SCANCODE_UP,    SDL_SCANCODE_W);
    cur[static_cast<int>(InputButton::Down)]         = is_down(SDL_SCANCODE_DOWN,  SDL_SCANCODE_S);
    cur[static_cast<int>(InputButton::Left)]         = is_down(SDL_SCANCODE_LEFT,  SDL_SCANCODE_A);
    cur[static_cast<int>(InputButton::Right)]        = is_down(SDL_SCANCODE_RIGHT, SDL_SCANCODE_D);
    cur[static_cast<int>(InputButton::A)]            = is_down(SDL_SCANCODE_Z,     SDL_SCANCODE_RETURN);
    cur[static_cast<int>(InputButton::B)]            = is_down(SDL_SCANCODE_X);
    cur[static_cast<int>(InputButton::L)]            = is_down(SDL_SCANCODE_Q);
    cur[static_cast<int>(InputButton::R)]            = is_down(SDL_SCANCODE_E);
    cur[static_cast<int>(InputButton::Start)]        = is_down(SDL_SCANCODE_ESCAPE, SDL_SCANCODE_BACKSPACE);
    cur[static_cast<int>(InputButton::Select)]       = is_down(SDL_SCANCODE_LSHIFT, SDL_SCANCODE_RSHIFT);
    cur[static_cast<int>(InputButton::FastForward)]  = false;
    cur[static_cast<int>(InputButton::FleetUpgrade)] = is_down(SDL_SCANCODE_F);

    // Gamepad held-state: polls directly so analog stick / triggers also count
    // even without button events this frame.
    if (controller != nullptr) {
        auto gc = [&](SDL_GameControllerButton b) {
            return SDL_GameControllerGetButton(controller, b) != 0;
        };
        auto axis = [&](SDL_GameControllerAxis a) {
            return SDL_GameControllerGetAxis(controller, a);
        };

        const int up    = static_cast<int>(InputButton::Up);
        const int down  = static_cast<int>(InputButton::Down);
        const int left  = static_cast<int>(InputButton::Left);
        const int right = static_cast<int>(InputButton::Right);

        if (gc(SDL_CONTROLLER_BUTTON_DPAD_UP))    cur[up]    = true;
        if (gc(SDL_CONTROLLER_BUTTON_DPAD_DOWN))  cur[down]  = true;
        if (gc(SDL_CONTROLLER_BUTTON_DPAD_LEFT))  cur[left]  = true;
        if (gc(SDL_CONTROLLER_BUTTON_DPAD_RIGHT)) cur[right] = true;

        const Sint16 ly = axis(SDL_CONTROLLER_AXIS_LEFTY);
        const Sint16 lx = axis(SDL_CONTROLLER_AXIS_LEFTX);
        if (ly < -kAxisDeadzone) cur[up]    = true;
        if (ly >  kAxisDeadzone) cur[down]  = true;
        if (lx < -kAxisDeadzone) cur[left]  = true;
        if (lx >  kAxisDeadzone) cur[right] = true;

        if (gc(SDL_CONTROLLER_BUTTON_A))              cur[static_cast<int>(InputButton::A)] = true;
        if (gc(SDL_CONTROLLER_BUTTON_B))              cur[static_cast<int>(InputButton::B)] = true;
        if (gc(SDL_CONTROLLER_BUTTON_X))              cur[static_cast<int>(InputButton::FastForward)] = true;
        if (gc(SDL_CONTROLLER_BUTTON_Y))              cur[static_cast<int>(InputButton::FleetUpgrade)] = true;
        if (gc(SDL_CONTROLLER_BUTTON_LEFTSHOULDER))   cur[static_cast<int>(InputButton::L)] = true;
        if (gc(SDL_CONTROLLER_BUTTON_RIGHTSHOULDER))  cur[static_cast<int>(InputButton::R)] = true;
        if (gc(SDL_CONTROLLER_BUTTON_START))          cur[static_cast<int>(InputButton::Start)] = true;
        if (gc(SDL_CONTROLLER_BUTTON_BACK))           cur[static_cast<int>(InputButton::Select)] = true;

        if (axis(SDL_CONTROLLER_AXIS_TRIGGERRIGHT) > kTriggerPressThreshold) {
            cur[static_cast<int>(InputButton::FastForward)] = true;
        }
        if (axis(SDL_CONTROLLER_AXIS_TRIGGERLEFT) > kTriggerPressThreshold) {
            cur[static_cast<int>(InputButton::FleetUpgrade)] = true;
        }
    }

    for (int i = 0; i < static_cast<int>(InputButton::COUNT); ++i) {
        if (pending_press[i]) {
            cur[i] = true;
        }
        pressed_now[i] = pending_press[i];
        released_now[i] = pending_release[i];
        pending_press[i] = false;
        pending_release[i] = false;
        if (cur[i]) {
            hold_time[i] += dt;
        } else {
            hold_time[i] = 0.0f;
        }
    }

    // Synthesize edge events from polled gamepad state so menu handlers (which
    // use pressed() = pending_press) see a press on rising edge.
    for (int i = 0; i < static_cast<int>(InputButton::COUNT); ++i) {
        if (cur[i] && ! prev[i]) {
            pressed_now[i] = true;
        }
        if (! cur[i] && prev[i]) {
            released_now[i] = true;
        }
    }
}

bool SDL2Input::pressed(InputButton btn) const {
    return pressed_now[static_cast<int>(btn)];
}

bool SDL2Input::held(InputButton btn) const {
    return cur[static_cast<int>(btn)];
}

bool SDL2Input::released(InputButton btn) const {
    return released_now[static_cast<int>(btn)];
}

bool SDL2Input::quit_requested() const {
    return quit;
}

float SDL2Input::held_duration(InputButton btn) const {
    return hold_time[static_cast<int>(btn)];
}
