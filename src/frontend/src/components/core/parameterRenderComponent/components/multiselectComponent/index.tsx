import Fuse from "fuse.js";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { mutateTemplate } from "../../../../../CustomNodes/helpers/mutate-template";
import { usePostTemplateValue } from "../../../../../controllers/API/queries/nodes/use-post-template-value";
import useAlertStore from "../../../../../stores/alertStore";
import { cn } from "../../../../../utils/utils";
import { default as ForwardedIconComponent } from "../../../../common/genericIconComponent";
import ShadTooltip from "../../../../common/shadTooltipComponent";
import { Button } from "../../../../ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
} from "../../../../ui/command";
import {
  Popover,
  PopoverContent,
  PopoverContentWithoutPortal,
  PopoverTrigger,
} from "../../../../ui/popover";
import type { InputProps, MultiselectComponentType } from "../../types";

export default function MultiselectComponent({
  disabled,
  value,
  options: defaultOptions,
  handleOnNewValue,
  combobox,
  editNode = false,
  id = "",
  hasRefreshButton,
  actionButton,
  name = "",
  nodeId,
  nodeClass,
  handleNodeClass,
  ...baseInputProps
}: InputProps<string[], MultiselectComponentType>): JSX.Element {
  const { t } = useTranslation();

  const [open, setOpen] = useState(false);
  const treatedValue = typeof value === "string" ? [value] : value;

  const refButton = useRef<HTMLButtonElement>(null);

  const PopoverContentDropdown = editNode
    ? PopoverContent
    : PopoverContentWithoutPortal;

  const [customValues, setCustomValues] = useState<string[]>([]);
  const [searchValue, setSearchValue] = useState("");
  const [filteredOptions, setFilteredOptions] = useState(defaultOptions);
  const [onlySelected, setOnlySelected] = useState(false);

  const [options, setOptions] = useState<string[]>(defaultOptions);

  const fuseOptions = new Fuse(options, { keys: ["name", "value"] });
  const fuseValues = new Fuse(treatedValue, { keys: ["name", "value"] });

  // API hooks for refresh button
  const postTemplateValue = usePostTemplateValue({
    parameterId: name,
    nodeId: nodeId,
    node: nodeClass,
  });
  const setErrorData = useAlertStore((state) => state.setErrorData);

  const searchRoleByTerm = async (v: string) => {
    const fuse = onlySelected ? fuseValues : fuseOptions;
    const searchValues = fuse.search(v);
    let filtered: string[] = searchValues.map((search) => search.item);
    if (!filtered.includes(v) && combobox && v) filtered = [v, ...filtered];
    setFilteredOptions(
      v
        ? filtered
        : onlySelected
          ? options.filter((x) => treatedValue.includes(x))
          : options,
    );
  };

  const handleRefreshButtonPress = async () => {
    if (!nodeId || !nodeClass || !handleNodeClass) return;

    await mutateTemplate(
      value,
      nodeId,
      nodeClass,
      handleNodeClass,
      postTemplateValue,
      setErrorData,
      name,
      undefined,
      undefined,
      "refresh",
    );
  };

  const handleActionButtonPress = async () => {
    if (!actionButton || !actionButton.action) return;
    if (!nodeId || !nodeClass || !handleNodeClass) return;

    await mutateTemplate(
      value,
      nodeId,
      nodeClass,
      handleNodeClass,
      postTemplateValue,
      setErrorData,
      name,
      undefined,
      undefined,
      actionButton.action,
    );
  };

  useEffect(() => {
    if (disabled && treatedValue.length > 0 && treatedValue[0] !== "") {
      handleOnNewValue({ value: [] }, { skipSnapshot: true });
    }
  }, [disabled]);

  useEffect(() => {
    searchRoleByTerm(searchValue);
  }, [onlySelected]);

  useEffect(() => {
    searchRoleByTerm(searchValue);
  }, [options]);

  useEffect(() => {
    setCustomValues(
      treatedValue.filter((v) => !defaultOptions.includes(v)) ?? [],
    );
    setOptions([
      ...treatedValue.filter((v) => !defaultOptions.includes(v) && v),
      ...defaultOptions,
    ]);
  }, [value]);

  useEffect(() => {
    if (open) {
      setOnlySelected(false);
      setSearchValue("");
      searchRoleByTerm("");
    }
  }, [open]);

  const handleOptionSelect = (currentValue) => {
    if (treatedValue.includes(currentValue)) {
      handleOnNewValue({
        value: treatedValue.filter((v) => v !== currentValue),
      });
    } else {
      handleOnNewValue({ value: [...treatedValue, currentValue] });
    }
  };

  const renderDropdownTrigger = () => (
    <PopoverTrigger asChild>
      <Button
        disabled={disabled}
        variant="primary"
        size="xs"
        role="combobox"
        ref={refButton}
        aria-expanded={open}
        data-testid={id}
        className={cn(
          editNode
            ? "dropdown-component-outline input-edit-node"
            : "dropdown-component-false-outline py-2",
          "w-full justify-between font-normal",
        )}
      >
        <span className="truncate" data-testid={`value-dropdown-${id}`}>
          {treatedValue.length > 0 &&
          options.find((option) => treatedValue.includes(option))
            ? treatedValue.join(", ")
            : t("components.multiselect.chooseOption")}
        </span>
        <ForwardedIconComponent
          name="ChevronsUpDown"
          className="ml-2 h-4 w-4 shrink-0 opacity-50"
        />
      </Button>
    </PopoverTrigger>
  );

  const renderSearchInput = () => (
    <div className="flex items-center border-b px-3">
      <ForwardedIconComponent
        name="search"
        className="mr-2 h-4 w-4 shrink-0 opacity-50"
      />
      <input
        onChange={(event) => {
          setSearchValue(event.target.value);
        }}
        placeholder={t("components.multiselect.searchPlaceholder")}
        className="flex h-9 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
      />
      <Button
        unstyled
        className="ml-2"
        onClick={() => setOnlySelected((old) => !old)}
      >
        <ForwardedIconComponent
          className="h-4 w-4"
          name={onlySelected ? "CheckCheck" : "Check"}
        />
      </Button>
    </div>
  );

  const renderOptionsList = () => (
    <CommandList className="overflow-y-scroll">
      <CommandEmpty>{t("components.multiselect.noValuesFound")}</CommandEmpty>
      <CommandGroup>
        {filteredOptions.map((option, index) => (
          <ShadTooltip key={index} delayDuration={700} content={option}>
            <div>
              <CommandItem
                value={option}
                onSelect={handleOptionSelect}
                className="items-center overflow-hidden truncate"
                data-testid={`${option}-${id ?? ""}-option`}
              >
                {(customValues.includes(option) || searchValue === option) && (
                  <span className="text-muted-foreground">
                    {t("components.multiselect.textPrefix")}&nbsp;
                  </span>
                )}
                <span className="truncate">{option}</span>
                <ForwardedIconComponent
                  name="Check"
                  className={cn(
                    "ml-auto h-4 w-4 shrink-0 text-primary",
                    treatedValue.includes(option) ? "opacity-100" : "opacity-0",
                  )}
                />
              </CommandItem>
            </div>
          </ShadTooltip>
        ))}
      </CommandGroup>
    </CommandList>
  );

  if (Object.keys(options).length === 0 && !combobox) {
    return (
      <div>
        <span className="text-sm italic">
          {t("components.multiselect.noParametersAvailable")}
        </span>
      </div>
    );
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      {renderDropdownTrigger()}
      <PopoverContentDropdown
        onOpenAutoFocus={(event) => event.preventDefault()}
        side="bottom"
        avoidCollisions={false}
        className="noflow nowheel nopan nodelete nodrag p-0"
        style={{ minWidth: refButton?.current?.clientWidth ?? "200px" }}
      >
        <Command>
          {renderSearchInput()}
          {renderOptionsList()}
          {(hasRefreshButton || actionButton) && (
            <div className="sticky bottom-0 border-t bg-background">
              {hasRefreshButton && (
                <CommandItem className="flex cursor-pointer items-center justify-start gap-2 truncate rounded-b-md py-3 text-xs font-semibold text-muted-foreground">
                  <Button
                    className="w-full"
                    unstyled
                    data-testid={`refresh-multiselect-list-${name}`}
                    onClick={() => {
                      handleRefreshButtonPress();
                    }}
                  >
                    <div className="flex items-center gap-2 pl-1">
                      <ForwardedIconComponent
                        name="RefreshCcw"
                        className={cn("refresh-icon h-3 w-3 text-primary")}
                      />
                      {t("dropdown.refreshList")}
                    </div>
                  </Button>
                </CommandItem>
              )}
              {actionButton && (
                <CommandItem className="flex cursor-pointer items-center justify-start gap-2 truncate rounded-b-md py-3 text-xs font-semibold text-muted-foreground">
                  <Button
                    className="w-full"
                    unstyled
                    data-testid={`action-multiselect-${name}`}
                    onClick={() => {
                      handleActionButtonPress();
                    }}
                  >
                    <div className="flex items-center gap-2 pl-1">
                      <ForwardedIconComponent
                        name={actionButton.icon || "Plus"}
                        className={cn("h-3 w-3")}
                      />
                      {actionButton.label}
                    </div>
                  </Button>
                </CommandItem>
              )}
            </div>
          )}
        </Command>
      </PopoverContentDropdown>
    </Popover>
  );
}
