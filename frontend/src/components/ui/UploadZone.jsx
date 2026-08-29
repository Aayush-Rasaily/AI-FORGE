import { useCallback, useRef, useState } from "react";
import { CheckCircle2, File, Loader2, Upload } from "lucide-react";

function UploadZone({
  accept,
  multiple = true,
  supportedText,
  title,
  files = [],
  onFilesSelected,
  disabled = false,
  processing = false,
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const handleFiles = useCallback(
    (fileList) => {
      const selected = Array.from(fileList || []);
      if (selected.length > 0) onFilesSelected(selected);
    },
    [onFilesSelected]
  );

  return (
    <div>
      <div
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (!disabled) handleFiles(event.dataTransfer.files);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        className={`forge-upload-zone ${dragging ? "forge-upload-zone-active" : ""}`}
      >
        <Upload className="h-5 w-5" />
        <div className="min-w-0 flex-1">
          <h3>{title}</h3>
          <p>{supportedText}</p>
        </div>
        <button
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
        >
          Select files
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple={multiple}
          accept={accept}
          className="hidden"
          disabled={disabled}
          onChange={(event) => handleFiles(event.target.files)}
        />
      </div>

      {processing && (
        <div className="forge-upload-processing" role="status">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Examining evidence and preparing the investigation record…</span>
        </div>
      )}

      {files.length > 0 && (
        <div className="forge-upload-files">
          <div className="forge-upload-files-heading">
            <strong>Selected evidence</strong>
            <span>{files.length} file(s)</span>
          </div>
          {files.map((file, index) => (
            <div className="forge-upload-file" key={`${file.name}-${index}`}>
              <File className="h-4 w-4" />
              <span title={file.name}>{file.name}</span>
              <small>{(file.size / 1024 / 1024).toFixed(2)} MB</small>
              <CheckCircle2 className="h-4 w-4" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default UploadZone;
