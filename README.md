# ESPHome marquee

Scroll UTF-8 text once from right to left using ESPHome's native font renderer. The component supports proportional fonts and 1-, 2-, 4-, and 8-bpp glyphs. It stores the message, but does not create a full-width bitmap or allocate during drawing. A rolling cursor avoids rescanning text that has already passed for fonts with nonnegative advances.

Add these sections to the YAML (merge `external_components` with your existing section if necessary):

```yaml
external_components:
  - source: github://adipierro/esphome-marquee@main
    components: [marquee]

marquee:
  id: scroll_text
  pixels_per_frame: 1
  on_finished:
    then:
      - display.page.show: next_page
```

ESPHome fetches the component from GitHub during configuration. This is an external component, so remove the old `globals:` entry of type `Marquee` and the old `esphome.includes` entry for the header. On recent ESPHome versions, user headers can be included *after* generated globals, which causes the `Marquee was not declared` error; the component makes its header available before those declarations.

Define an ESPHome font and initialize the marquee once in your existing `esphome:` block:

```yaml
esphome:
  name: my-display
  on_boot:
    priority: -100
    then:
      - lambda: |-
          id(scroll_text).set_text("Hello!", id(message_font));

font:
  - file: "gfonts://Roboto Condensed"
    id: message_font
    size: 14
    bpp: 4
```

In your display page's lambda, call `id(scroll_text).draw(it, 8, Color(255, 255, 255));`. The y coordinate is the top of the font's line box. The optional fourth argument is the background color used for antialiasing; it should match the display background. The call does not clear the display.

Use `id(scroll_text).progress()` to get the fraction of the full scroll from `0.0f` to `1.0f`, including the distance across the display and the text's rightmost extent. It is zero before the first draw and after a reset or new message, and one once scrolling finishes. The display width is captured on the first draw; reset the marquee if the display size changes. For example, after drawing the text in the same display lambda:

```cpp
const int bar_width = static_cast<int>(it.get_width() * id(scroll_text).progress());
if (bar_width > 0)
  it.filled_rectangle(0, it.get_height() - 2, bar_width, 2, Color(255, 255, 255));
```

See [examples/matrix.yaml](examples/matrix.yaml) for a complete configuration with an SSD1306 display and page switching. Change the display platform and pins for your matrix. Define the glyphs you need in the font's `glyphs:` configuration; ESPHome draws its usual missing-glyph placeholder for unsupported characters. Invalid UTF-8 terminates the displayed text, matching ESPHome's renderer.

Call `set_text(new_text, id(message_font))` whenever the message or font changes. It copies the string, measures it, and restarts the scroll. Call `reset()` to replay the current message. `on_finished` runs once after the final visible glyph or trailing advance has left the display, deferred until after drawing returns. You can use any ESPHome actions there; define `next_page` in your display's pages as shown in the example. A reset or new message before the deferred action runs cancels that pending notification. The `finished()` method also remains available and stays true until reset or new text.

The cursor uses actual glyph advances and bearings, including overhangs. Fonts with negative advances remain correct but require rescanning from the beginning on each frame. ESPHome's normal renderer determines glyph shaping and alpha blending; this does not implement text shaping or multiline layout. Empty text completes after the initial traversal of the display width.

Scrolling advances by `pixels_per_frame` pixels each time `draw()` is called after the first call. This setting defaults to 1; with a steady `update_interval: 40ms`, that is about 25 pixels per second. Use a larger value to move more pixels per draw. A late or missed update slows the scroll instead of skipping ahead, and no progress occurs while the page is inactive. Each call counts as a frame, so call `draw()` once per display update. Buffer swaps are not synchronized to the panel's DMA refresh; irregular display updates can still affect the timing of visible movement.

Call `set_pixels_per_frame(pixels)` to change the step at runtime without restarting the message; zero pauses it. The YAML setting accepts values from 1 to 65535. `set_text()` and `reset()` retain the selected step. The former `set_speed()` API has been removed; adjust `pixels_per_frame` and the display's `update_interval` instead.
