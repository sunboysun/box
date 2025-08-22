import os
import tempfile
from flask import Flask, request, render_template, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
import PyPDF2
import io

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 在生產環境中請更換為安全的密鑰
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB 限制

# 建立上傳資料夾
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() == 'pdf'

def remove_pdf_password(input_path, password, output_path):
    """
    移除PDF密碼
    """
    try:
        with open(input_path, 'rb') as input_file:
            pdf_reader = PyPDF2.PdfReader(input_file)
            
            # 檢查PDF是否有密碼保護
            if pdf_reader.is_encrypted:
                # 嘗試解密
                if pdf_reader.decrypt(password):
                    pdf_writer = PyPDF2.PdfWriter()
                    
                    # 複製所有頁面到新的PDF
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        pdf_writer.add_page(page)
                    
                    # 寫入新的PDF檔案
                    with open(output_path, 'wb') as output_file:
                        pdf_writer.write(output_file)
                    
                    return True, "PDF密碼成功移除"
                else:
                    return False, "密碼錯誤，無法解密PDF"
            else:
                # PDF沒有密碼，直接複製
                with open(output_path, 'wb') as output_file:
                    output_file.write(input_file.read())
                return True, "PDF沒有密碼保護，已複製檔案"
                
    except Exception as e:
        return False, f"處理PDF時發生錯誤: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('沒有選擇檔案', 'error')
        return redirect(request.url)
    
    file = request.files['file']
    password = request.form.get('password', '')
    
    if file.filename == '':
        flash('沒有選擇檔案', 'error')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # 保留原始檔名（包含中文字符）
        original_filename = file.filename
        
        # 生成安全的內部檔案名稱用於儲存
        import time
        timestamp = str(int(time.time()))
        safe_filename = secure_filename(original_filename)
        input_filename = f"{timestamp}_{safe_filename}"
        
        # 為了檔案系統安全，內部使用時間戳記檔名
        safe_output_filename = f"{timestamp}_unlocked_{safe_filename}"
        if not safe_output_filename.endswith('.pdf'):
            safe_output_filename += '.pdf'
        
        # 保留原檔名用於下載顯示，前面加上「解密_」
        base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
        display_filename = f"解密_{base_name}.pdf"
        
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
        output_path = os.path.join(app.config['PROCESSED_FOLDER'], safe_output_filename)
        
        # 儲存上傳的檔案
        file.save(input_path)
        
        # 處理PDF
        success, message = remove_pdf_password(input_path, password, output_path)
        
        # 清理上傳的檔案
        if os.path.exists(input_path):
            os.remove(input_path)
        
        if success:
            flash(message, 'success')
            return render_template('download.html', 
                                 internal_filename=safe_output_filename,
                                 display_filename=display_filename)
        else:
            flash(message, 'error')
            return redirect(url_for('index'))
    
    else:
        flash('請上傳PDF檔案', 'error')
        return redirect(url_for('index'))

@app.route('/download/<internal_filename>/<display_filename>')
def download_file(internal_filename, display_filename):
    try:
        file_path = os.path.join(app.config['PROCESSED_FOLDER'], internal_filename)
        if os.path.exists(file_path):
            # 使用原始檔名作為下載檔名
            return send_file(file_path, as_attachment=True, download_name=display_filename)
        else:
            flash('檔案不存在', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'下載檔案時發生錯誤: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
