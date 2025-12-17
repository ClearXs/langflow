from importlib import import_module

_dynamic_imports = {
    # Input components
    "ETLAPIInputComponent": "api_input",
    "ETLCDCInputComponent": "cdc_input",
    "ETLCSVInputComponent": "csv_input",
    "ETLCustomInputComponent": "custom_input",
    "ETLExcelInputComponent": "excel_input",
    "ETLFeignInputComponent": "feign_input",
    "ETLFileInputComponent": "file_input",
    "ETLKafkaInputComponent": "kafka_input",
    "ETLTableInputComponent": "table_input",
    # Output components
    "ETLAPIOutputComponent": "api_output",
    "ETLCSVOutputComponent": "csv_output",
    "ETLExcelOutputComponent": "excel_output",
    "ETLFeignOutputComponent": "feign_output",
    "ETLKafkaOutputComponent": "kafka_output",
    "ETLTableOutputComponent": "table_output",
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
