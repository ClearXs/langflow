import FileTableInputComponent from "@/components/core/parameterRenderComponent/components/fileTableInputComponent";
import InputFileComponent from "@/components/core/parameterRenderComponent/components/inputFileComponent";
import type {
  FileComponentType,
  InputProps,
} from "@/components/core/parameterRenderComponent/types";

export default function CustomInputFileComponent({
  value,
  file_path,
  handleOnNewValue,
  disabled,
  fileTypes,
  isList,
  tempFile = true,
  editNode = false,
  id,
}: InputProps<string, FileComponentType>): JSX.Element {
  // If tempFile is false, use the file table input component
  if (tempFile === false) {
    return (
      <FileTableInputComponent
        value={value}
        file_path={file_path}
        handleOnNewValue={handleOnNewValue}
        disabled={disabled}
        fileTypes={fileTypes}
        isList={isList}
        editNode={editNode}
        id={`filetable_${id}`}
      />
    );
  }

  // Otherwise, use the traditional file upload component
  return (
    <InputFileComponent
      value={value}
      file_path={file_path}
      handleOnNewValue={handleOnNewValue}
      disabled={disabled}
      fileTypes={fileTypes}
      isList={isList}
      tempFile={tempFile}
      editNode={editNode}
      id={`inputfile_${id}`}
    />
  );
}
