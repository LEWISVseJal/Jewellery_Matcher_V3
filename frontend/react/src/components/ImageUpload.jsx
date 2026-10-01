import {
  useRef,
  useState,
} from "react";

import CameraModal from "./CameraModal";


function ImageUpload({
  image,
  onImageChange,
}) {
  const fileInputRef =
    useRef(null);

  const cameraInputRef =
    useRef(null);

  const [cameraOpen, setCameraOpen] =
    useState(false);

  const [dragging, setDragging] =
    useState(false);


  function handleFile(file) {

    if (!file) {
      return;
    }


    if (!file.type.startsWith("image/")) {
      return;
    }


    onImageChange(file);
  }


  function handleInputChange(event) {

    const file =
      event.target.files?.[0];

    handleFile(file);

    event.target.value = "";
  }


  function handleDrop(event) {

    event.preventDefault();

    setDragging(false);

    const file =
      event.dataTransfer.files?.[0];

    handleFile(file);
  }


  function handleDragOver(event) {

    event.preventDefault();

    setDragging(true);
  }


  function handleDragLeave(event) {

    event.preventDefault();

    setDragging(false);
  }


  if (image) {

    return (
      <div className="image-upload-preview">

        <div className="image-preview-wrapper">

          <img
            src={URL.createObjectURL(image)}
            alt="Jewellery preview"
          />

        </div>


        <div className="image-preview-details">

          <span>
            {image.name}
          </span>

          <button
            type="button"
            onClick={() =>
              onImageChange(null)
            }
          >
            Remove
          </button>

        </div>


        <button
          type="button"
          className="change-image-button"
          onClick={() =>
            fileInputRef.current?.click()
          }
        >
          Change Image
        </button>


        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          hidden
          onChange={handleInputChange}
        />

      </div>
    );
  }


  return (
    <>
      <div
        className={`image-upload-box ${
          dragging
            ? "dragging"
            : ""
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >

        <div className="upload-icon">
          ↑
        </div>


        <h3>
          Upload jewellery image
        </h3>


        <p>
          Drag & drop your image here
        </p>


        <span className="upload-or">
          or
        </span>


        <div className="upload-actions">

          <button
            type="button"
            onClick={() =>
              fileInputRef.current?.click()
            }
          >
            Browse Image
          </button>


          <button
            type="button"
            onClick={() =>
              setCameraOpen(true)
            }
          >
            Take Photo
          </button>

        </div>


        <small>
          JPG, JPEG, PNG, WEBP or BMP
        </small>


        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          hidden
          onChange={handleInputChange}
        />

      </div>


      {cameraOpen && (
        <CameraModal
          onCapture={(file) => {

            handleFile(file);

            setCameraOpen(false);

          }}
          onClose={() =>
            setCameraOpen(false)
          }
        />
      )}

    </>
  );
}


export default ImageUpload;