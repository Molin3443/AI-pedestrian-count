document.getElementById('uploadForm').addEventListener('submit', function(event) {
    event.preventDefault(); // Предотвращаем перезагрузку страницы

    const formData = new FormData();
    const fileInput = document.getElementById('fileInput');
    
    if (!fileInput.files.length) {
        alert("Пожалуйста, выберите файл.");
        return;
    }

    formData.append('file', fileInput.files[0]);

    const processBtn = document.getElementById('processBtn');
    processBtn.disabled = true;
    processBtn.textContent = "Обработка...";

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log(data); // Логируем ответ сервера

        const resultSection = document.getElementById('resultSection');
        const objectCountSpan = document.getElementById('objectCount');
        const mediaContainer = document.getElementById('mediaContainer');

        if (data.error) {
            alert("Ошибка при обработке: " + data.error);
            processBtn.disabled = false;
            processBtn.textContent = "Запустить обработку";
            return;
        }

        // Показываем секцию с результатом
        resultSection.style.display = 'block';
        objectCountSpan.textContent = data.count || 0;
        mediaContainer.innerHTML = ''; // Чистим контейнер перед вставкой

        const filename = data.filename;
        const ext = filename.split('.').pop().toLowerCase();

        let mediaElement;
        if (ext === 'mp4' || ext === 'mov') {
            mediaElement = document.createElement('video');
            mediaElement.controls = true;
        } else {
            mediaElement = document.createElement('img');
        }
        mediaElement.src = `/result/${filename}`;

        mediaContainer.appendChild(mediaElement);

    })
    .catch(error => {
        console.error('Error:', error);
        alert("Произошла сетевая ошибка.");
    })
    .finally(() => {
        processBtn.disabled = false;
        processBtn.textContent = "Запустить обработку";
    });
});