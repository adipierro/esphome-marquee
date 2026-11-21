"""Exercise completion and reset timing using small ESPHome API stand-ins."""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

STUB = r'''#pragma once
#include <cstdint>
#include <functional>
#include <vector>
namespace esphome {
inline uint32_t now_ms = 0;
inline uint32_t millis() { return now_ms; }
struct Color { Color(int, int, int) {} };
class Component { public: virtual void loop() {} };
template<typename... T> class Trigger {
 public:
  std::function<void()> callback;
  void trigger() { if (callback) callback(); }
};
namespace display { class Display { public: int get_width() { return 10; } }; }
namespace font {
struct Glyph { int advance, offset_x, width; };
class Font {
 public:
  std::vector<Glyph> glyphs{{2, 0, 2}};
  const std::vector<Glyph> &get_glyphs() const { return glyphs; }
  const Glyph *find_glyph(uint32_t) const { return &glyphs[0]; }
  void print(int, int, display::Display *, Color, const char *, Color) {}
};
}
namespace unicode {
inline uint32_t extract_unicode_codepoint(const char *s, size_t *length) {
  *length = *s ? 1 : 0;
  return static_cast<unsigned char>(*s);
}
}
}
'''

TEST = r'''#include "components/marquee/marquee.h"
#include <cassert>
int main() {
  esphome::marquee::Marquee marquee(10);
  esphome::display::Display display;
  esphome::font::Font font;
  int calls = 0;
  marquee.get_finished_trigger()->callback = [&] { ++calls; };
  auto draw = [&] { marquee.draw(display, 0, esphome::Color(1, 1, 1)); };
  marquee.set_text("A", &font);
  esphome::now_ms = 0;
  draw();
  esphome::now_ms = 1200;
  draw();
  assert(marquee.finished() && calls == 0); // Drawing never invokes actions.
  marquee.loop();
  marquee.loop();
  draw();
  assert(calls == 1);                       // Exactly once per pass.
  marquee.reset();
  esphome::now_ms = 1300;
  draw();
  esphome::now_ms = 2500;
  draw();
  marquee.set_text("B", &font);           // Cancels pending notification.
  marquee.loop();
  assert(calls == 1 && !marquee.finished());
  draw();
  esphome::now_ms = 3700;
  draw();
  marquee.loop();
  assert(calls == 2);
}
'''


class CompletionTest(unittest.TestCase):
    def test_completion_callback(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            (base / "stub.h").write_text(STUB)
            for name in ("components/display/display.h", "components/font/font.h",
                         "components/unicode/unicode.h", "core/automation.h",
                         "core/component.h", "core/hal.h"):
                path = base / "esphome" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('#include "stub.h"\n')
            source = base / "test.cpp"
            source.write_text(TEST)
            binary = base / "test"
            subprocess.run(["c++", "-std=c++17", "-I", str(base), "-I", str(ROOT),
                            str(source), "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    unittest.main()
