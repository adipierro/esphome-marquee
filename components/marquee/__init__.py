import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID

DEPENDENCIES = ["display", "font"]
AUTO_LOAD = ["unicode"]
MULTI_CONF = True

marquee_ns = cg.esphome_ns.namespace("marquee")
Marquee = marquee_ns.class_("Marquee", cg.Component)

CONFIG_SCHEMA = cv.Schema({cv.GenerateID(): cv.declare_id(Marquee)}).extend(
    cv.COMPONENT_SCHEMA
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
