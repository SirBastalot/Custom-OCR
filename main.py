from PIL import Image

threshold_font_color = 126
image = Image.open("Val_di_Ledro+Regina_del_Lago+Sektor_D_1.png")
width, height = image.size
image = image.convert("RGB")


def clamp(var, min_val, max_val):
    return max(min_val, min(var, max_val))


def filter(threshold=8):
    filter_matrix = [[0 for _ in range(height)] for _ in range(width)]

    # Füllen der Filter-Matrix
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


def histogram(filter_matrix):
    hcolumn = [0] * width  # Initialisieren mit der Breite des Bildes
    hrow = [0] * height  # Initialisieren mit der Höhe des Bildes

    # Berechnung des Spalten-Histogramms
    for column in range(width):
        count = 0
        for row in range(height):
            if filter_matrix[column][row] == 0:
                count += 1
        hcolumn[column] = count

    # Berechnung des Zeilen-Histogramms
    for row in range(height):
        count = 0
        for column in range(width):
            if filter_matrix[column][row] == 0:
                count += 1
        hrow[row] = count

    return hcolumn, hrow


cutX = [0] * 6
cutX[0] = 0
cutX[1] = 370
cutX[2] = 420
cutX[3] = 480
cutX[4] = 540
cutX[5] = width - 1

def optXgrid(matrix):
    optimizationOffset = 10
    hcolumn = histogram(matrix)[0]

    for i in range (width):
        print(f"{i} - {hcolumn[i]}")

    for cut in range (1,5):
        for offset in range (optimizationOffset + 1):
            if hcolumn[cutX[cut] + offset] == 0:
                cutX[cut] += offset
                break
            if hcolumn[cutX[cut] - offset] == 0:
                cutX[cut] -= offset
                break


filter_matrix = filter()
hcol, hrow = histogram(filter_matrix)
optXgrid(filter_matrix)

print("Spalten-Histogramm:", hcol)
print("Zeilen-Histogramm:", hrow)
print("Optimierte X-Schnitte:", cutX)
