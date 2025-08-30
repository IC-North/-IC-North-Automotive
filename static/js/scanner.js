function startScanner(targetInputId) {
    if (Quagga.initialized) {
        Quagga.stop();
    }

    Quagga.init({
        inputStream: {
            type: "LiveStream",
            constraints: {
                facingMode: "environment",
                aspectRatio: { min: 1, max: 2 },
                width: { min: 640, ideal: 1280 },
                height: { min: 480, ideal: 720 }
            },
            area: { top: "25%", right: "25%", left: "25%", bottom: "25%" }
        },
        decoder: {
            readers: [
                "code_128_reader",
                "ean_reader",
                "ean_8_reader",
                "code_39_reader",
                "code_39_vin_reader",
                "upc_reader",
                "upc_e_reader",
                "i2of5_reader",
                "qr_reader"
            ]
        }
    }, function (err) {
        if (err) {
            console.error(err);
            alert("Camera kon niet worden gestart. Controleer permissies.");
            return;
        }
        Quagga.start();
        Quagga.initialized = true;
        document.getElementById("scanner-container").style.display = "block";
    });

    Quagga.onDetected(function (data) {
        document.getElementById(targetInputId).value = data.codeResult.code;
        Quagga.stop();
        document.getElementById("scanner-container").style.display = "none";
    });
}