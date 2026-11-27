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
struct Color { Color(int, int, int) {} };
class Component { public: virtual void loop() {} };
template<typename... T> class Trigger {
 public:
  std::function<void()> callback;
  void trigger() { if (callback) callback(); }
};
namespace display { class Display { public: int width = 10; int get_width() { return width; } }; }
namespace font {
struct Glyph { int advance, offset_x, width; };
class Font {
 public:
  std::vector<Glyph> glyphs{{2, 0, 2}};
  std::vector<int> positions;
  const std::vector<Glyph> &get_glyphs() const { return glyphs; }
  const Glyph *find_glyph(uint32_t) const { return &glyphs[0]; }
  void print(int x, int, display::Display *, Color, const char *, Color) { positions.push_back(x); }
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
#include <cmath>
int main() {
  esphome::marquee::Marquee marquee;
  esphome::display::Display display;
  esphome::font::Font font;
  int calls = 0;
  marquee.get_finished_trigger()->callback = [&] { ++calls; };
  auto draw = [&] { marquee.draw(display, 0, esphome::Color(1, 1, 1)); };
  assert(marquee.progress() == 0.0f);
  marquee.set_text("A", &font);
  assert(marquee.progress() == 0.0f);
  for (int i = 0; i < 13; ++i) draw();
  assert(marquee.finished() && calls == 0); // Drawing never invokes actions.
  assert(marquee.progress() == 1.0f);
  marquee.loop();
  marquee.loop();
  draw();
  assert(calls == 1);                       // Exactly once per pass.
  marquee.reset();
  assert(marquee.progress() == 0.0f);
  for (int i = 0; i < 13; ++i) draw();
  marquee.set_text("B", &font);           // Cancels pending notification.
  marquee.loop();
  assert(calls == 1 && !marquee.finished());
  for (int i = 0; i < 13; ++i) draw();
  marquee.loop();
  assert(calls == 2);

  // The default step advances exactly one pixel per draw.
  marquee.set_text("A", &font);
  font.positions.clear();
  draw();  // Starts just outside the display.
  assert(marquee.progress() == 0.0f);
  draw();
  draw();
  draw();
  assert((font.positions == std::vector<int>{9, 8, 7}));
  assert(std::fabs(marquee.progress() - 0.25f) < 0.0001f); // 3 / (10 + 2)

  // Pausing and changing the step preserve the current position.
  marquee.set_pixels_per_frame(0);
  draw();
  assert(font.positions.back() == 7);
  assert(std::fabs(marquee.progress() - 0.25f) < 0.0001f);
  marquee.set_pixels_per_frame(2);
  draw();
  assert(font.positions.back() == 5);
  marquee.reset();
  assert(marquee.progress() == 0.0f);
  draw();
  draw();
  assert(font.positions.back() == 8);  // Reset retains the step.

  // Completion is still deferred and delivered once in frame mode.
  for (int i = 0; i < 6; ++i) draw();
  assert(marquee.finished() && calls == 2);
  assert(marquee.progress() == 1.0f);  // Overshoot is clamped.
  marquee.loop();
  marquee.loop();
  assert(calls == 3);

  // An empty message traverses the display width; a zero-width display
  // completes without dividing by zero.
  marquee.set_text("", &font);
  assert(marquee.progress() == 0.0f);
  draw();
  draw();
  assert(std::fabs(marquee.progress() - 0.2f) < 0.0001f);
  display.width = 0;
  marquee.set_text("", &font);
  draw();
  assert(marquee.finished() && marquee.progress() == 1.0f);
}
'''


class CompletionTest(unittest.TestCase):
    def test_completion_callback(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            (base / "stub.h").write_text(STUB)
            for name in ("components/display/display.h", "components/font/font.h",
                         "components/unicode/unicode.h", "core/automation.h",
                         "core/component.h"):
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
