from esphome import automation
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID

DEPENDENCIES = ["display", "font"]
AUTO_LOAD = ["unicode"]
MULTI_CONF = True

marquee_ns = cg.esphome_ns.namespace("marquee")
Marquee = marquee_ns.class_("Marquee", cg.Component)
CONF_ON_FINISHED = "on_finished"
CONF_PIXELS_PER_FRAME = "pixels_per_frame"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(Marquee),
        cv.Optional(CONF_PIXELS_PER_FRAME): cv.int_range(min=1, max=65535),
        cv.Optional(CONF_ON_FINISHED): automation.validate_automation(single=True),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    if CONF_PIXELS_PER_FRAME in config:
        cg.add(var.set_pixels_per_frame(config[CONF_PIXELS_PER_FRAME]))
    if CONF_ON_FINISHED in config:
        await automation.build_automation(
            var.get_finished_trigger(), [], config[CONF_ON_FINISHED]
        )
