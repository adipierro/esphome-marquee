#pragma once

#include <algorithm>
#include <cstdint>
#include <string>

#include "esphome/components/display/display.h"
#include "esphome/components/font/font.h"
#include "esphome/components/unicode/unicode.h"
#include "esphome/core/automation.h"
#include "esphome/core/component.h"
#include "esphome/core/hal.h"

namespace esphome::marquee {

// One right-to-left pass. Coordinates use the same top-left origin as Font::print.
class Marquee : public Component {
 public:
  explicit Marquee(uint16_t speed = 25) : speed_(speed) {}

  void set_text(const std::string &text, esphome::font::Font *font) {
    text_ = text;
    font_ = font;
    measure_();
    reset();
  }

  void reset() {
    first_byte_ = 0;
    first_offset_ = 0;
    position_ = 0;
    remainder_ = 0;
    started_ = false;
    finished_ = false;
    pending_finished_ = false;
  }

  void set_speed(uint16_t pixels_per_second) { speed_ = pixels_per_second; }
  bool finished() const { return finished_; }
  Trigger<> *get_finished_trigger() { return &finished_trigger_; }

  void loop() override {
    if (pending_finished_) {
      pending_finished_ = false;
      finished_trigger_.trigger();
    }
  }

  void draw(esphome::display::Display &display, int y, esphome::Color foreground,
            esphome::Color background = esphome::Color(0, 0, 0)) {
    if (font_ == nullptr || finished_)
      return;

    const int width = display.get_width();
    const uint32_t now = esphome::millis();
    if (!started_) {
      position_ = width;
      started_ = true;
    } else {
      const uint64_t movement = uint64_t(uint32_t(now - last_ms_)) * speed_ + remainder_;
      position_ -= static_cast<int64_t>(movement / 1000);
      remainder_ = movement % 1000;
    }
    last_ms_ = now;

    if (position_ + right_extent_ <= 0) {
      finished_ = true;
      pending_finished_ = true;
      return;
    }

    // Negative advances are unusual; retain correctness by scanning from the start.
    if (monotonic_) {
      while (first_byte_ < valid_bytes_) {
        size_t length;
        const auto cp = esphome::unicode::extract_unicode_codepoint(text_.c_str() + first_byte_, &length);
        const auto *glyph = find_glyph_(cp);
        const int advance = advance_(glyph);
        const int right = glyph ? glyph->offset_x + glyph->width : advance;
        if (position_ + first_offset_ + right > 0)
          break;
        first_byte_ += length;
        first_offset_ += advance;
      }
    }

    size_t byte = first_byte_;
    int64_t offset = first_offset_;
    while (byte < valid_bytes_) {
      size_t length;
      const char *p = text_.c_str() + byte;
      const auto cp = esphome::unicode::extract_unicode_codepoint(p, &length);
      const auto *glyph = find_glyph_(cp);
      const int advance = advance_(glyph);
      const int64_t pen = position_ + offset;
      // A later glyph can have a negative bearing, so use the minimum bearing
      // across the font instead of the current glyph's left edge.
      if (monotonic_ && pen + min_bearing_ >= width)
        break;
      const int64_t left = pen + (glyph ? glyph->offset_x : 0);
      const int64_t right = left + (glyph ? glyph->width : advance);
      if (right > 0 && left < width) {
        char character[5] = {};
        for (size_t i = 0; i < length; ++i)
          character[i] = p[i];
        font_->print(static_cast<int>(pen), y, &display, foreground, character, background);
      }
      byte += length;
      offset += advance;
    }
  }

 private:
  const esphome::font::Glyph *find_glyph_(uint32_t cp) const {
    // Some ESPHome versions cannot safely search an empty glyph table.
    return font_->get_glyphs().empty() ? nullptr : font_->find_glyph(cp);
  }

  int advance_(const esphome::font::Glyph *glyph) const {
    if (glyph != nullptr)
      return glyph->advance;
    const auto &glyphs = font_->get_glyphs();
    return glyphs.empty() ? 0 : glyphs[0].advance;
  }

  void measure_() {
    valid_bytes_ = 0;
    right_extent_ = 0;
    min_bearing_ = 0;
    monotonic_ = true;
    if (font_ == nullptr)
      return;
    const auto &glyphs = font_->get_glyphs();
    for (size_t i = 0; i < glyphs.size(); ++i)
      min_bearing_ = std::min(min_bearing_, glyphs[i].offset_x);

    int64_t pen = 0;
    while (valid_bytes_ < text_.size()) {
      size_t length;
      const auto cp = esphome::unicode::extract_unicode_codepoint(text_.c_str() + valid_bytes_, &length);
      if (length == 0)
        break;  // Match ESPHome's handling of invalid UTF-8 and embedded NUL.
      const auto *glyph = find_glyph_(cp);
      const int advance = advance_(glyph);
      const int64_t right = pen + (glyph ? glyph->offset_x + glyph->width : advance);
      right_extent_ = std::max(right_extent_, right);
      monotonic_ = monotonic_ && advance >= 0;
      pen += advance;
      valid_bytes_ += length;
    }
    right_extent_ = std::max(right_extent_, pen);
  }

  std::string text_;
  esphome::font::Font *font_{nullptr};
  size_t valid_bytes_{0};
  size_t first_byte_{0};
  int64_t first_offset_{0};
  int64_t position_{0};
  int64_t right_extent_{0};
  int min_bearing_{0};
  uint32_t last_ms_{0};
  uint64_t remainder_{0};
  uint16_t speed_{25};
  bool monotonic_{true};
  bool started_{false};
  bool finished_{false};
  bool pending_finished_{false};
  Trigger<> finished_trigger_;
};

}  // namespace esphome::marquee
