
async function startScanner(targetFieldId) {
    try {
        // Sluit oude streams af
        if (window.currentStream) {
            window.currentStream.getTracks().forEach(track => track.stop());
        }

        const constraints = {
            video: { facingMode: "environment" }
        };
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        window.currentStream = stream;

        // Videoveld fullscreen tonen
        let video = document.createElement("video");
        video.setAttribute("playsinline", true);
        video.style.position = "fixed";
        video.style.top = "0";
        video.style.left = "0";
        video.style.width = "100%";
        video.style.height = "100%";
        video.style.zIndex = "9999";
        document.body.appendChild(video);
        video.srcObject = stream;
        await video.play();

        // BarcodeDetector fallback voor iOS
        let detector;
        if ('BarcodeDetector' in window) {
            detector = new BarcodeDetector({ formats: ['qr_code', 'code_128', 'code_39', 'ean_13', 'upc_a'] });
        }

        const canvas = document.createElement("canvas");
        const context = canvas.getContext("2d");

        async function scanFrame() {
            if (video.readyState === video.HAVE_ENOUGH_DATA) {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                context.drawImage(video, 0, 0, canvas.width, canvas.height);

                if (detector) {
                    try {
                        const barcodes = await detector.detect(canvas);
                        if (barcodes.length > 0) {
                            let code = barcodes[0].rawValue;
                            document.getElementById(targetFieldId).value = code;

                            stopScanner(video, stream);
                            return;
                        }
                    } catch (e) {
                        console.error("Detectie fout:", e);
                    }
                }
            }
            requestAnimationFrame(scanFrame);
        }

        scanFrame();
    } catch (err) {
        alert("Camera toegang geweigerd of niet beschikbaar.");
        console.error(err);
    }
}

function stopScanner(video, stream) {
    stream.getTracks().forEach(track => track.stop());
    video.remove();
}
