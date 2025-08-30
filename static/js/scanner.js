
function startScanner(targetInputId) {
    if (Quagga.initialized) {
        Quagga.stop();
    }

    Quagga.init({
        inputStream: {
            type: "LiveStream",
            constraints: {
                facingMode: "environment",
                width: { min: 640, ideal: 1920 },
                height: { min: 480, ideal: 1080 }
            }
        },
        decoder: {
            readers: ["code_128_reader", "ean_reader", "ean_8_reader", "code_39_reader", "upc_reader", "upc_e_reader", "codabar_reader", "i2of5_reader", "2of5_reader", "code_93_reader", "qr_reader"]
        }
    }, function(err) {
        if (err) {
            console.error(err);
            return;
        }
        Quagga.start();
        Quagga.initialized = true;
    });

    Quagga.onDetected(function(result) {
        if (result && result.codeResult && result.codeResult.code) {
            document.getElementById(targetInputId).value = result.codeResult.code;
            Quagga.stop();
            Quagga.initialized = false;
        }
    });
}
