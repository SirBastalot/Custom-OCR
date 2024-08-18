from PIL import Image
import os
import requests
import mysql.connector
from mysql.connector import Error


api_key = 'K87966375588957'
api_url = 'https://api.ocr.space/parse/image'
def clamp(var, min_val, max_val):
    return max(min_val, min(var, max_val))


def filter(image, width, height, threshold_font_color, threshold=8, ):
    filter_matrix = [[0 for _ in range(height)] for _ in range(width)]

    for x in range(width):
        for y in range(height):
            min_x = clamp(x - threshold, 0, width - 1)
            max_x = clamp(x + threshold, 0, width - 1)
            filter_matrix[x][y] = 1
            for new_x in range(min_x, max_x + 1):
                value = image.getpixel((new_x, y))[0]
                if value < threshold_font_color:
                    filter_matrix[x][y] = 0
    return filter_matrix


def histogram(matrix, width, height):
    hcolumn = [0] * width
    hrow = [0] * height

    for column in range(width):
        count = 0
        for row in range(height):
            if matrix[column][row] == 0:
                count += 1
        hcolumn[column] = count

    for row in range(height):
        count = 0
        for column in range(width):
            if matrix[column][row] == 0:
                count += 1
        hrow[row] = count

    return hcolumn, hrow


def optXgrid(hcolumn, width):
    cutX = [0] * 6
    cutX[0] = 0
    cutX[1] = 370
    cutX[2] = 420
    cutX[3] = 480
    cutX[4] = 540
    cutX[5] = width - 1
    optimizationOffset = 10

    for cut in range(1, 5):
        for offset in range(optimizationOffset + 1):
            if hcolumn[cutX[cut] + offset] == 0:
                cutX[cut] += offset
                break
            if hcolumn[cutX[cut] - offset] == 0:
                cutX[cut] -= offset
                break
    return cutX


def optYgrid(hrow, height):
    lookForEmpty = True
    lineCount = 0
    cutY = [0] * 100

    for i in range(height):

        if lookForEmpty and hrow[i] == 0:
            lookForEmpty = False
            cutY[lineCount] = i
            lineCount += 1
        elif not lookForEmpty and hrow[i] != 0:
            lookForEmpty = True

    return cutY[:lineCount]  # just the important lines...


def getSquares(matrix, optimalXCuts, optimalYCuts):
    square = [0] * ((len(optimalXCuts) - 1) * (len(optimalYCuts) - 1))
    currentSquare = 0
    for y in range(1, len(optimalYCuts)):
        for x in range(1, len(optimalXCuts)):
            startX = optimalXCuts[x - 1]
            endX = optimalXCuts[x]
            startY = optimalYCuts[y - 1]
            endY = optimalYCuts[y]
            count = 0
            for m in range(startX, endX):
                for n in range(startY, endY):
                    value = matrix[m][n]
                    if value == 0:
                        count += 1
            square[currentSquare] = count
            currentSquare += 1
    return square


def classify(squares, min):
    squareClass = ["Beschreibung"] * len(squares)
    for i in range(len(squares)):
        j = i % 5 + 1  # 0-4 + 1
        if j == 1:
            if squares[i] > min:
                squareClass[i] = "Name"
        elif j == 2:
            if squares[i] > min:
                squareClass[i] = "Seillänge"
            elif squareClass[i - 5] == "Seillänge":
                squareClass[i] = "Seillänge"
        elif j == 3:
            squareClass[i] = "Schwierigkeit"
        elif j == 4:
            squareClass[i] = "Länge"
    linesToDelete = []
    for i in range(1, len(squares) + 1, 5):
        if (squareClass[i] == "Seillänge"):
            linesToDelete.append(i)
    for i in range(len(linesToDelete)):
        del squareClass[linesToDelete[i] - 1:linesToDelete[i] + 4]
        del squareClass[linesToDelete[i] - 1:linesToDelete[i] + 4]
    return squares, squareClass


def stich(squareClass, image, optXCuts, optYCuts):
    i = 0
    x1, x2 = 0 - 1, 1 - 1
    y1, y2 = 0, 1
    route = 1
    tempBeschreibungen = []
    while (y2 < (len(optYCuts) - 1)) or (x2 < (len(optXCuts) - 1)):
        x1+=1
        x2+=1
        if x1 == 5:  #normal loop
            x1, x2 = 0 , 1
            y1+=1
            y2+=1

        if squareClass[i] == "Beschreibung" and x2 == 1: #bis zum rechten element springen
            x1+=4
            x2+=4
            i+=4

        if squareClass[i] == "Beschreibung" and x2 == 5: #beschreibung in die liste hinzufügen
            tempBeschreibungen.append(i)

        if squareClass[i] == "Name" and x1 == 0 and i > 1: #nicht erstes element, nicht
            newFileName = f"{route}:Beschreibung.png"
            handleDescription(image, optXCuts, optYCuts, tempBeschreibungen, newFileName)
            tempBeschreibungen.clear()
            route +=1

        if not x1 == 1 and x2 != 5: #Seillänge ist eh leer und keine Beschreibungen speichern
            saveImage(image, f"generatedImages/{route}:{squareClass[i]}", optXCuts[x1], optXCuts[x2], optYCuts[y1], optYCuts[y2])
        i+=1
    #ausgeben
    newFileName = f"{route}:Beschreibung.png"
    handleDescription(image, optXCuts, optYCuts, tempBeschreibungen, newFileName)
    tempBeschreibungen.clear()
    route = 1

def handleDescription(image, optXCuts, optYCuts, tempBeschreibungen, newFileName):
    total_width = 0
    total_height = 0

    images = []

    for index in tempBeschreibungen:
        cropped_image = getImageFromIndex(image, optXCuts, optYCuts, index)
        images.append(cropped_image)
        total_width = max(total_width, cropped_image.width)
        total_height += cropped_image.height

    new_image = Image.new('RGB', (total_width, total_height))

    # Füge jedes Bild an die richtige Position ein
    current_height = 0
    for img in images:
        new_image.paste(img, (0, current_height))  # Füge das Bild an die aktuelle Höhe ein
        current_height += img.height  # Aktualisiere die Höhe für das nächste Bild

    # Optional: Speichere oder zeige das resultierende Bild
    new_image.save(f"generatedImages/{newFileName}")

def getImageFromIndex(image, optXCuts, optYCuts, index):
    sqaures = len(optXCuts) - 1
    x_index = index % sqaures
    y_index = index // sqaures

    # Bestimme die Koordinaten des Rechtecks
    x1 = optXCuts[x_index]
    x2 = optXCuts[x_index + 1]
    y1 = optYCuts[y_index]
    y2 = optYCuts[y_index + 1]

    # Schneide das Rechteck aus dem Bild
    cropped_image = image.crop((x1, y1, x2, y2))

    return cropped_image
def saveImage(image, name, x1, x2, y1, y2):
    cropped_image = image.crop((x1, y1, x2, y2))
    cropped_image.save(f'{name}.png')


def extract(file_name, threshold_font_color=126):
    image = Image.open(file_name).convert("RGB")
    width, height = image.size
    matrix = filter(image, width, height, threshold_font_color)
    hcolumn, hrow = histogram(matrix, width, height)
    optimalXCuts = optXgrid(hcolumn, width)
    optimalYCuts = optYgrid(hrow, height)
    squares = getSquares(matrix, optimalXCuts, optimalYCuts)
    squares, squareClass = classify(squares, 500)
    stich(squareClass, image, optimalXCuts, optimalYCuts)


def getImagesFromDir(directory_path):
    for filename in os.listdir(directory_path):
        if filename.endswith('.png'):
            file_path = os.path.join(directory_path, filename)
            extract(file_path)

getImagesFromDir("/home/bastian/PycharmProjects/Custom-OCR/")

def ocr_image(image_path):
    with open(image_path, 'rb') as image_file:
        payload = {
            'apikey': api_key,
            'language': 'eng',  # Deutsch
            'isOverlayRequired': False,
            'scale': True,
            'OCREngine': 2,
            'isTable': False,
            'detectOrientation': False
        }
        files = {'file': image_file}
        response = requests.post(api_url, data=payload, files=files)

        if response.status_code == 200:
            result = response.json()
            parsed_text = result.get('ParsedResults')[0].get('ParsedText')
            return parsed_text
        else:
            print("No API resonse:")
            return None


def process_images_in_directory(directory_path):
    recognized_texts = {}  # Dictionary zur Speicherung der erkannten Texte

    # Gehe alle Dateien im Verzeichnis durch
    for filename in sorted(os.listdir(directory_path)):
        if filename.lower().endswith(".png"):
            file_path = os.path.join(directory_path, filename)
            print(f"Processing file: {file_path}")
            text = ocr_image(file_path)
            if text:
                recognized_texts[filename] = text
            else:
                print(f"Error processing file: {filename}")

    return recognized_texts


# Beispielaufruf: Verzeichnis mit Bildern angeben
directory = '/home/bastian/PycharmProjects/Custom-OCR/generatedImages'  # Pfad zu deinem Verzeichnis
result_texts = process_images_in_directory(directory)




def insert_route(sektor_id, routen_name, schwierigkeit, routenlaenge, routen_beschreibung):
    try:
        # Verbindung zur MySQL-Datenbank herstellen
        connection = mysql.connector.connect(
            host='localhost',  # Ändere das, wenn deine Datenbank auf einem anderen Server läuft
            database='climbingroutes_db',
            user='root',  # Setze hier deinen MySQL-Benutzernamen
            password='maRJN6D12bWB'    # Setze hier dein MySQL-Passwort
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # SQL-Insert-Befehl für die Tabelle Routen
            insert_query = """
            INSERT INTO Routen (sektor_id, routen_name, schwierigkeit, routenlaenge, routen_beschreibung)
            VALUES (%s, %s, %s, %s, %s)
            """
            # Werte, die eingefügt werden sollen
            values = (sektor_id, routen_name, schwierigkeit, routenlaenge, routen_beschreibung)

            # SQL-Befehl ausführen
            cursor.execute(insert_query, values)

            # Änderungen in der Datenbank übernehmen
            connection.commit()

            print("Route erfolgreich eingefügt.")

    except Error as e:
        print(f"Fehler beim Einfügen der Route: {e}")

    finally:
        # Verbindung schließen
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL-Verbindung geschlossen.")

# Beispielaufruf der Funktion


# Erkannten Text ausgeben
for filename, text in result_texts.items():
    print(f"Text aus {filename}:")
    print(text)
    print('---')
