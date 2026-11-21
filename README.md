# ESPHome marquee

Scroll UTF-8 text once from right to left using ESPHome's native font renderer. The component supports proportional fonts and 1-, 2-, 4-, and 8-bpp glyphs. It stores the message, but does not create a full-width bitmap or allocate during drawing. A rolling cursor avoids rescanning text that has already passed for fonts with nonnegative advances.

Copy the `components/marquee` directory beside your ESPHome YAML, preserving this layout:

```text
config/
  matrix.yaml
  components/
    marquee/
      __init__.py
      marquee.h
```

Add these sections to the YAML (merge `external_components` with your existing section if necessary):

```yaml
external_components:
  - source:
      type: local
      path: components
    components: [marquee]

marquee:
  id: scroll_text
```

The files must be available to the machine performing ESPHome's configuration and build, including remote builds. This is an external component, so remove the old `globals:` entry of type `Marquee` and the old `esphome.includes` entry for the header. On recent ESPHome versions, user headers can be included *after* generated globals, which causes the `Marquee was not declared` error; the component makes its header available before those declarations.

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

See [examples/matrix.yaml](examples/matrix.yaml) for a complete configuration with an SSD1306 display and page switching. Change the display platform and pins for your matrix. Define the glyphs you need in the font's `glyphs:` configuration; ESPHome draws its usual missing-glyph placeholder for unsupported characters. Invalid UTF-8 terminates the displayed text, matching ESPHome's renderer.

Call `set_text(new_text, id(message_font))` whenever the message or font changes. It copies the string, measures it, and restarts the scroll. Use `set_speed(pixels_per_second)` to change the default speed of 25 pixels per second; zero pauses motion. Call `reset()` to replay the current message. `finished()` becomes true after the final visible glyph or trailing advance has left the display; it remains true until reset or new text. Check it outside the display lambda to switch pages, as in the example. When a page is inactive, elapsed time continues to accrue until the next draw; call `reset()` when replaying it.

The cursor uses actual glyph advances and bearings, including overhangs. Fonts with negative advances remain correct but require rescanning from the beginning on each frame. ESPHome's normal renderer determines glyph shaping and alpha blending; this does not implement text shaping or multiline layout. Empty text completes after the initial traversal of the display width.
