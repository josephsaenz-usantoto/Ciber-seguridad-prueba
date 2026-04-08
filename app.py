from flask import Flask, render_template, request, session, send_file, flash, redirect, url_for, make_response
from PIL import Image, ImageDraw, ImageFont
import random, io, os, re
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# -------------------------
# Helpers, los helpers se usan en varias vistas
# -------------------------
def _only_digits(text: str) -> str:
    """Extrae solo los dígitos de un string."""
    import re as _re
    return _re.sub(r'\D+', '', text or '')

def _no_cache_response(html):
    """Devuelve una respuesta HTML con cabeceras no-cache para evitar páginas en el historial."""
    resp = make_response(html)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

# -------------------------
# Home (menú)
# -------------------------
@app.route('/home')
def home():
    return _no_cache_response(render_template('home.html'))

# -------------------------
# CAPTCHA aritmético
# -------------------------
@app.route('/', methods=['GET', 'POST'])
def captcha1():
    if request.method == 'POST':
        user_answer = request.form.get('captcha')
        real_answer = session.get('captcha_answer')

        if user_answer and real_answer and user_answer.strip() == str(real_answer):
            # Marca de sesión SOLO para la siguiente vista /bienvenido
            session['just_logged_in'] = True
            flash("CAPTCHA correcto. ¡Bienvenido!", "success")
            return redirect(url_for('bienvenido'))
        else:
            flash("CAPTCHA incorrecto. Inténtalo de nuevo.", "danger")
            return redirect(url_for('captcha1'))

    cache_buster = int(datetime.utcnow().timestamp())
    return _no_cache_response(render_template('captcha1.html', cache_buster=cache_buster))

@app.route('/captcha_image')
def captcha_image():
    # Aritmético con +, -, *, /
    operator = random.choice(['+', '-', '*', '/'])

    if operator == '+':
        num1 = random.randint(1, 9)
        num2 = random.randint(1, 9)
        answer = num1 + num2
        op_symbol = '+'
    elif operator == '-':
        num1 = random.randint(1, 9)
        num2 = random.randint(1, 9)
        answer = num1 - num2
        op_symbol = '−'  # visual
    elif operator == '*':
        num1 = random.randint(1, 9)
        num2 = random.randint(1, 9)
        answer = num1 * num2
        op_symbol = '×'  # visual
    elif operator == '/':
        # Generamos una operación de división que siempre de un número entero
        # Elegimos la respuesta y el segundo número, y calculamos el primero
        answer = random.randint(2, 9)
        num2 = random.randint(2, 9)
        num1 = answer * num2
        op_symbol = '÷'

    session['captcha_answer'] = answer
    captcha_text = f"{num1} {op_symbol} {num2} = ?"

    img = Image.new('RGB', (180, 60), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()

    for _ in range(15):
        x1, y1 = random.randint(0, 180), random.randint(0, 60)
        x2, y2 = x1 + random.randint(-8, 8), y1 + random.randint(-8, 8)
        draw.line((x1, y1, x2, y2), fill=(220, 220, 220), width=1)

    draw.text((20, 15), captcha_text, font=font, fill=(0, 0, 0))

    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    # La imagen sí puede cachearse; no aplicamos no-store aquí.
    return send_file(img_io, mimetype='image/png')




# -------------------------
# CAPTCHA por identificación (2 pasos)
# -------------------------
@app.route('/captcha-id', methods=['GET', 'POST'])
def captcha2():
    if request.method == 'POST':
        user_id = _only_digits(request.form.get('identificacion'))

        if not user_id or len(user_id) < 6 or len(user_id) > 12:
            flash("La identificación debe tener entre 6 y 12 dígitos.", "danger")
            return redirect(url_for('captcha2'))

        session['user_id'] = user_id

        # Dos posiciones distintas 1-captcha1adas
        p1 = random.randint(1, len(user_id))
        p2 = random.randint(1, len(user_id))
        while p2 == p1:
            p2 = random.randint(1, len(user_id))
        session['id_positions'] = sorted([p1, p2])

        return redirect(url_for('captcha22'))

    return _no_cache_response(render_template('captcha2.html'))

@app.route('/captcha-id/verify', methods=['GET', 'POST'])
def captcha22():
    user_id = session.get('user_id')
    pos = session.get('id_positions')

    if not user_id or not pos:
        flash("Primero ingresa tu identificación.", "danger")
        return redirect(url_for('captcha2'))

    if request.method == 'POST':
        d1 = _only_digits(request.form.get('digit1'))
        d2 = _only_digits(request.form.get('digit2'))

        if len(d1) != 1 or len(d2) != 1:
            flash("Debes ingresar un dígito en cada campo.", "danger")
            return redirect(url_for('captcha22'))

        ok = (d1 == user_id[pos[0]-1]) and (d2 == user_id[pos[1]-1])

        if ok:
            # Marca de sesión SOLO para la siguiente vista /bienvenido
            session['just_logged_in'] = True
            flash("Verificación por identificación completada. ¡Bienvenido!", "success")
            # (Opcional) limpiar datos sensibles
            session.pop('id_positions', None)
            # session.pop('user_id', None)  # si no lo necesitas después
            return redirect(url_for('bienvenido'))
        else:
            flash("Los dígitos no coinciden. Inténtalo de nuevo.", "danger")
            # Reasignar nuevas posiciones
            p1 = random.randint(1, len(user_id))
            p2 = random.randint(1, len(user_id))
            while p2 == p1:
                p2 = random.randint(1, len(user_id))
            session['id_positions'] = sorted([p1, p2])
            return redirect(url_for('captcha22'))

    return _no_cache_response(render_template('captcha22.html', positions=pos))




# -------------------------
# CAPTCHA aritmético (versión 2)
# -------------------------
@app.route('/captcha3', methods=['GET', 'POST'])
def captcha3():
    """Ruta para la página principal del nuevo CAPTCHA."""
    if request.method == 'POST':
        user_answer = request.form.get('captcha')
        # CORRECCIÓN: Usar la clave de sesión 'captcha3_answer'
        real_answer = session.get('captcha3_answer')

        if user_answer and real_answer is not None and user_answer.strip() == str(real_answer):
            session['just_logged_in'] = True
            flash("CAPTCHA 3 correcto. ¡Bienvenido!", "success")
            return redirect(url_for('bienvenido'))
        else:
            flash("CAPTCHA 3 incorrecto. Inténtalo de nuevo.", "danger")
            return redirect(url_for('captcha3'))

    cache_buster = int(datetime.utcnow().timestamp())
    # Esta línea asume que tienes un archivo 'captcha3.html' para el formulario
    return _no_cache_response(render_template('captcha3.html', cache_buster=cache_buster))


@app.route('/captcha3_image')
def captcha3_image():
    op_symbols = {'+': '+', '-': '−', '*': '×', '/': '÷'}
    # Se ha modificado para usar siempre 4 números
    num_count = 4
    numbers = [random.randint(1, 10) for _ in range(num_count)]
    operators = [random.choice(['+', '-', '*', '/']) for _ in range(num_count - 1)]
    expression_parts = []
    for i in range(num_count):
        expression_parts.append(str(numbers[i]))
        if i < num_count - 1:
            expression_parts.append(operators[i])
    
    expression_text = ' '.join(expression_parts)
    
    try:
        eval_expression = expression_text.replace('×', '*').replace('−', '-').replace('÷', '/')
        answer = eval(eval_expression)
        
        # Validar si el resultado es un número entero
        if isinstance(answer, float) and answer != int(answer):
            return captcha3_image() # Regenerar si el resultado no es entero
        
        answer = int(answer)
    except (ZeroDivisionError, SyntaxError):
        # Regenerar si hay una división por cero o un error de sintaxis
        return captcha3_image()
        
    session['captcha3_answer'] = answer
    
    for i in range(num_count - 1):
        expression_parts[2*i + 1] = op_symbols[operators[i]]
        
    captcha_text = f"{' '.join(expression_parts)} = ?"

    # El ancho de la imagen se ajusta automáticamente
    img_width = 180 + (num_count - 3) * 30 
    img = Image.new('RGB', (img_width, 60), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except IOError:
        font = ImageFont.load_default()
    
    # Agregar líneas para distorsionar
    for _ in range(20):
        x1, y1 = random.randint(0, img_width), random.randint(0, 60)
        x2, y2 = x1 + random.randint(-8, 8), y1 + random.randint(-8, 8)
        draw.line((x1, y1, x2, y2), fill=(220, 220, 220), width=1)

    draw.text((10, 15), captcha_text, font=font, fill=(0, 0, 0))

    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')



# -------------------------
# CAPTCHA de Secuencia Lógica (opción 3)
# -------------------------
@app.route('/captcha4', methods=['GET', 'POST'])
def captcha4():
    """Ruta para la página del CAPTCHA de secuencia lógica."""
    
    # La respuesta correcta es una lista con los días de la semana ordenados
    # Esto se guarda en la sesión para que el servidor la pueda validar
    dias_correctos = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    session['dias_correctos'] = dias_correctos
    
    # Se crea una copia de la lista y se mezcla para mostrar al usuario
    dias_mezclados = list(dias_correctos)
    random.shuffle(dias_mezclados)
    
    if request.method == 'POST':
        # Recibe la lista ordenada por el usuario desde el frontend
        user_sequence = request.form.getlist('dias[]')
        
        if user_sequence == session.get('dias_correctos'):
            session['just_logged_in'] = True
            flash("CAPTCHA de secuencia correcto. ¡Bienvenido!", "success")
            return redirect(url_for('bienvenido'))
        else:
            flash("CAPTCHA de secuencia incorrecto. Inténtalo de nuevo.", "danger")
            return redirect(url_for('captcha4'))

    return _no_cache_response(render_template('captcha4.html', dias=dias_mezclados))





# -------------------------
# Bienvenido
# -------------------------
@app.route('/bienvenido')
def bienvenido():
    # Solo mostrar si viene de un login/captcha recién completado
    if session.get('just_logged_in'):
        # Consumir la bandera para que al volver atrás NO se muestre de nuevo
        session.pop('just_logged_in', None)
        return _no_cache_response(render_template('welcome.html'))
    # Si intenta llegar sin pasar por verificación, lo mandamos al menú
    flash("Por favor, inicia desde el menú.", "danger")
    return redirect(url_for('home'))

# -------------------------
# Arranque
# -------------------------
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8090)
