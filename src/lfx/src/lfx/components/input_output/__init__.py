from importlib import import_module

_dynamic_imports = {
    # Input components
    "ETLTableInputComponent": "table_input",
    "ETLFileInputComponent": "file_input",
    "ETLAPIInputComponent": "api_input",
    "ETLKafkaInputComponent": "kafka_input",
    "ETLCDCInputComponent": "cdc_input",
    # Output components
    "ETLTableOutputComponent": "table_output",
    "ETLExcelOutputComponent": "excel_output",
    "ETLCSVOutputComponent": "csv_output",
    "ETLAPIOutputComponent": "api_output",
}


def __getattr__(attr_name: str):
    if attr_name not in _dynamic_imports:
        msg = f"module {__name__!r} has no attribute {attr_name!r}"
        raise AttributeError(msg)
    module_name = _dynamic_imports[attr_name]
    module = import_module(f".{module_name}", package=__name__)
    component_class = getattr(module, attr_name)
    globals()[attr_name] = component_class
    return component_class


__all__ = list(_dynamic_imports.keys())
