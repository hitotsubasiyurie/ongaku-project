import importlib
import pkgutil


PLUGINS = {}


for _, module_name, _ in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f"{__name__}.{module_name}")

    plugin_main = getattr(module, "main", None)
    plugin_name = getattr(module, "PLUGIN_NAME", module_name)

    if callable(plugin_main):
        PLUGINS[plugin_name] = plugin_main

