import {
  useEffect,
  useRef,
  useState,
} from "react";


function CameraModal({
  onCapture,
  onClose,
}) {
  const videoRef = useRef(null);

  const streamRef = useRef(null);

  const [error, setError] =
    useState("");


  useEffect(() => {
    let mounted = true;


    async function startCamera() {
      try {

        const stream =
          await navigator.mediaDevices.getUserMedia(
            {
              video: {
                facingMode: {
                  ideal: "environment",
                },
              },
              audio: false,
            }
          );


        if (!mounted) {

          stream
            .getTracks()
            .forEach(
              (track) =>
                track.stop()
            );

          return;
        }


        streamRef.current =
          stream;


        if (videoRef.current) {

          videoRef.current.srcObject =
            stream;

          await videoRef.current.play();

        }

      } catch (cameraError) {

        console.error(
          "Camera error:",
          cameraError
        );

        setError(
          "Unable to access the camera. Please allow camera permission and try again."
        );

      }
    }


    startCamera();


    return () => {

      mounted = false;

      if (streamRef.current) {

        streamRef.current
          .getTracks()
          .forEach(
            (track) =>
              track.stop()
          );

      }

    };

  }, []);


  function capturePhoto() {

    const video =
      videoRef.current;

    if (!video) {
      return;
    }


    const canvas =
      document.createElement(
        "canvas"
      );


    canvas.width =
      video.videoWidth;

    canvas.height =
      video.videoHeight;


    const context =
      canvas.getContext(
        "2d"
      );


    context.drawImage(
      video,
      0,
      0,
      canvas.width,
      canvas.height
    );


    canvas.toBlob(
      (blob) => {

        if (!blob) {
          return;
        }


        const file =
          new File(
            [blob],
            `jewellery-${Date.now()}.jpg`,
            {
              type: "image/jpeg",
            }
          );


        onCapture(file);

      },
      "image/jpeg",
      0.92
    );
  }


  return (
    <div
      className="camera-overlay"
      onMouseDown={(event) => {

        if (
          event.target ===
          event.currentTarget
        ) {
          onClose();
        }

      }}
    >

      <div className="camera-modal">

        <div className="camera-header">

          <div>

            <span>
              Camera
            </span>

            <h2>
              Take a jewellery photo
            </h2>

          </div>


          <button
            type="button"
            className="camera-close"
            onClick={onClose}
          >
            ×
          </button>

        </div>


        {error ? (

          <div className="camera-error">
            {error}
          </div>

        ) : (

          <div className="camera-preview">

            <video
              ref={videoRef}
              playsInline
              muted
            />

            <div className="camera-frame" />

          </div>

        )}


        <div className="camera-controls">

          {!error && (
            <button
              type="button"
              className="camera-capture"
              onClick={capturePhoto}
            >
              <span />
            </button>
          )}

        </div>

      </div>

    </div>
  );
}


export default CameraModal;