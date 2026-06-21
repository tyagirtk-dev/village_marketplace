import os
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)
UPLOAD_FOLDER = 'static/hero_slides'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Bootstrap UI template
HTML_UI = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <title>Slide Manager</title>
</head>
<body class="bg-light">
    <div class="container py-5">
        <div class="card shadow-sm p-4">
            <h2 class="mb-4 text-success">🎨 Hero Slider Manager</h2>
            
            <form method="POST" enctype="multipart/form-data" class="row g-3 mb-4">
                <div class="col-auto">
                    <input type="file" name="file" class="form-control" required>
                </div>
                <div class="col-auto">
                    <button type="submit" class="btn btn-success">Upload Slide</button>
                </div>
            </form>

            <table class="table table-hover">
                <thead class="table-light">
                    <tr><th>Slide Name</th><th>Action</th></tr>
                </thead>
                <tbody>
                    {% for f in files %}
                    <tr>
                        <td>{{ f }}</td>
                        <td><a href="{{ url_for('delete_file', filename=f) }}" class="btn btn-sm btn-danger">Delete</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            <a href="/" class="btn btn-outline-secondary mt-3">Back to Main Shop</a>
        </div>
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            ext = os.path.splitext(file.filename)[1]
            count = len(os.listdir(UPLOAD_FOLDER)) + 1
            file.save(os.path.join(UPLOAD_FOLDER, f'slide{count}{ext}'))
            return redirect('/')
    files = os.listdir(UPLOAD_FOLDER)
    return render_template_string(HTML_UI, files=files)

@app.route('/delete/<filename>')
def delete_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect('/')

if __name__ == '__main__':
    app.run(port=5001)
