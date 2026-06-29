import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import uuid
from ultralytics import YOLO
import shutil

# Настройки
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'mov'}
MODEL_PATH = "yolov8n.pt"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

model = YOLO(MODEL_PATH)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        original_name = secure_filename(file.filename)
        ext = original_name.rsplit('.', 1)[-1]
        unique_id = str(uuid.uuid4())[:8]
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_input.{ext}")
        output_path = os.path.join(app.config['RESULTS_FOLDER'], f"{unique_id}_output.{ext}")

        file.save(input_path)

        try:
            # Очистка папок 
            exp_dir = 'runs/detect/exp'
            if os.path.exists(exp_dir):
                for f in os.listdir(exp_dir):
                    file_path = os.path.join(exp_dir, f)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f"Failed to delete {file_path}. Reason: {e}")

            # Очистка папки runs/detect/results
            results_base = 'runs/detect/results'
            if os.path.exists(results_base):
                for f in os.listdir(results_base):
                    file_path = os.path.join(results_base, f)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f"Failed to delete {file_path}. Reason: {e}")
            # Детекция
            results = model.predict(
                source=input_path,
                project=app.config['RESULTS_FOLDER'],
                name="",  # Пустой каталог
                save=True,
                imgsz=640,
                conf=0.25
            )

            # Получаем коробки
            boxes = results[0].boxes

            # Подсчет объектов (работает даже если boxes = None)
            if boxes is None:
                pedestrians_count = 0
            else:
            # Индексы пешеходов (класс 0)
                pedestrian_indices = (boxes.cls == 0).nonzero(as_tuple=False).squeeze(-1)
                pedestrians_count = len(pedestrian_indices)
            # Статистика
            stats = {
                "filename": f"{unique_id}_output.{ext}",
                "count": pedestrians_count,
                "confidences": boxes.conf[pedestrian_indices].tolist(),
                "classes": boxes.cls[pedestrian_indices].tolist()
            }

            # Перемещаем готовое изображение
            result_files = [
                f for f in os.listdir('runs/detect/exp')
                if f.endswith(ext)
            ]

            if result_files:
                detected_file = result_files[0]
                os.rename(
                    os.path.join('runs/detect/exp', detected_file),
                    output_path
                )

                # Очистка
                os.remove(input_path)
                for f in os.listdir('runs/detect/exp'):
                    os.remove(os.path.join('runs/detect/exp', f))
                
            return jsonify(stats)

        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
        
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/result/<path:filename>')
def get_result(filename):
    """
    Ищет файл в папке runs/detect/results/predict-N/
    """
    base = "runs/detect/"

    # Находим папку results
    subfolders = os.listdir(base)
    results_folder = next((f for f in subfolders if f.startswith("results")), None)

    # Находим папку predict-N
    predict_folders = os.listdir(os.path.join(base, results_folder))
    predict_folder = next((f for f in predict_folders if f.startswith("predict")), None)

    # Находим файл с нужным расширением
    ext = filename.split(".")[-1]
    files = [f for f in os.listdir(os.path.join(base, results_folder, predict_folder)) if f.endswith(ext)]
    image_file = files[0]

    return send_from_directory(
        directory=os.path.join(base, results_folder, predict_folder),
        path=image_file
    )
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)