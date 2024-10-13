import csv
import os
import re
from shapely.geometry import shape, Polygon, Point
from shapely.wkt import loads
from shapely.ops import transform
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from tkcolorpicker import askcolor  # Biblioteca para o seletor de cores
import pyproj
from functools import partial

# Função para verificar e criar diretórios
if not os.path.exists('input'):
    os.makedirs('input')
if not os.path.exists('filtered'):
    os.makedirs('filtered')
if not os.path.exists('kml'):
    os.makedirs('kml')

def filter_records(input_file, center_coords, radius_meters):
    try:
        # Converter raio de metros para graus (aproximado)
        radius_degrees = radius_meters / 111000  # 1 grau de latitude é aproximadamente 111 km
        center_point = Point(center_coords)

        output_file = filedialog.asksaveasfilename(initialdir='filtered', defaultextension=".csv", initialfile="sicor_glebas_wkt_filtered.csv", title="Salvar arquivo filtrado", filetypes=[("CSV files", "*.csv")])
        if not output_file:
            return

        with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
            reader = csv.reader(infile, delimiter=';')
            writer = csv.writer(outfile, delimiter=';')

            # Escrever cabeçalho no arquivo de saída
            header = next(reader)
            writer.writerow(header)

            for row in reader:
                try:
                    # Carregar o polígono WKT da coluna correspondente
                    polygon = loads(row[3])

                    # Verificar se o polígono está dentro do raio fornecido
                    if isinstance(polygon, Polygon) and polygon.distance(center_point) <= radius_degrees:
                        writer.writerow(row)
                except Exception as e:
                    # Caso haja erro ao ler o polígono, apenas ignore esse registro
                    continue
        messagebox.showinfo("Sucesso", f"Registros filtrados salvos em: {output_file}")
    except FileNotFoundError:
        messagebox.showerror("Erro", f"Arquivo {input_file} não encontrado.")

# Função para conversão de WKT para KML
def wkt_to_kml(wkt_polygon, output_kml_file, opacity_color, area_hectares):
    polygon = loads(wkt_polygon)
    coords = list(polygon.exterior.coords)

    # Criar a estrutura KML
    kml = Element('kml', xmlns="http://www.opengis.net/kml/2.2")
    placemark = SubElement(kml, 'Placemark')
    name = SubElement(placemark, 'name')
    name.text = f"Polygon - Área: {area_hectares:.2f} ha"
    style = SubElement(placemark, 'Style')
    line_style = SubElement(style, 'LineStyle')
    line_color = SubElement(line_style, 'color')
    line_color.text = "ff0000ff"  # Vermelho (no formato ABGR)
    line_width = SubElement(line_style, 'width')
    line_width.text = "2"
    poly_style = SubElement(style, 'PolyStyle')
    poly_color = SubElement(poly_style, 'color')
    poly_color.text = opacity_color  # Cor de opacidade fornecida pelo usuário

    polygon_kml = SubElement(placemark, 'Polygon')
    outer_boundary = SubElement(polygon_kml, 'outerBoundaryIs')
    linear_ring = SubElement(outer_boundary, 'LinearRing')
    coordinates = SubElement(linear_ring, 'coordinates')

    # Adicionar coordenadas ao KML
    coords_str = " ".join([f"{lon},{lat},0" for lon, lat, *_ in coords])
    coordinates.text = coords_str

    # Escrever o arquivo KML
    tree = ElementTree(kml)
    with open(output_kml_file, 'wb') as f:
        tree.write(f, xml_declaration=True, encoding='utf-8')

# Função para gerar um único arquivo KML contendo todos os polígonos
def generate_combined_kml(selected_file, opacity_color):
    output_kml_file = filedialog.asksaveasfilename(initialdir='kml', defaultextension=".kml", initialfile="combined_polygons.kml", title="Salvar arquivo KML combinado", filetypes=[("KML files", "*.kml")])
    if not output_kml_file:
        return

    kml = Element('kml', xmlns="http://www.opengis.net/kml/2.2")
    document = SubElement(kml, 'Document')

    with open(selected_file, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader)  # Pular o cabeçalho
        line_number = 1
        for row in reader:
            try:
                wkt_polygon = row[3]
                polygon = loads(wkt_polygon)
                coords = list(polygon.exterior.coords)

                placemark = SubElement(document, 'Placemark')
                name = SubElement(placemark, 'name')
                name.text = f"Polygon {line_number}"
                style = SubElement(placemark, 'Style')
                line_style = SubElement(style, 'LineStyle')
                line_color = SubElement(line_style, 'color')
                line_color.text = "ff0000ff"  # Vermelho (no formato ABGR)
                line_width = SubElement(line_style, 'width')
                line_width.text = "2"
                poly_style = SubElement(style, 'PolyStyle')
                poly_color = SubElement(poly_style, 'color')
                poly_color.text = opacity_color  # Cor de opacidade fornecida pelo usuário

                polygon_kml = SubElement(placemark, 'Polygon')
                outer_boundary = SubElement(polygon_kml, 'outerBoundaryIs')
                linear_ring = SubElement(outer_boundary, 'LinearRing')
                coordinates = SubElement(linear_ring, 'coordinates')

                # Adicionar coordenadas ao KML
                coords_str = " ".join([f"{lon},{lat},0" for lon, lat, *_ in coords])
                coordinates.text = coords_str

                line_number += 1
            except Exception as e:
                continue

    # Escrever o arquivo KML
    tree = ElementTree(kml)
    with open(output_kml_file, 'wb') as f:
        tree.write(f, xml_declaration=True, encoding='utf-8')

# GUI usando Tkinter
def run_gui():
    def on_filter():
        try:
            url = url_entry.get()
            radius = float(radius_entry.get())
            year = year_entry.get()
            input_filename = f"sicor_glebas_wkt_{year}.csv"
            input_file = os.path.join('input', input_filename)
            coords = extract_coords_from_url(url)

            if coords is None:
                messagebox.showerror("Erro", "URL inválida. Não foi possível extrair as coordenadas.")
                return

            filter_records(input_file, coords, radius)
        except ValueError:
            messagebox.showerror("Erro", "Por favor, insira um valor numérico para o raio.")

    def extract_coords_from_url(url):
        match = re.search(r'@([-\d\.]+),([-\d\.]+)', url)
        if match:
            latitude, longitude = map(float, match.groups())
            return (longitude, latitude)
        return None

    def on_generate_kml():
        selected_file = selected_file_entry.get()
        if not selected_file or not os.path.exists(selected_file):
            messagebox.showerror("Erro", "Arquivo filtrado não selecionado ou não encontrado.")
            return

        # Obter a cor de opacidade do campo de entrada
        color = color_entry.get()
        if not color:
            messagebox.showerror("Erro", "Cor não fornecida.")
            return

        # Converter a cor para o formato ABGR exigido pelo KML
        opacity_color = "7d" + color[5:] + color[3:5] + color[1:3]

        # Obter diretório para salvar os arquivos KML
        kml_directory = kml_directory_entry.get()
        if not kml_directory or not os.path.exists(kml_directory):
            messagebox.showerror("Erro", "Por favor, selecione um diretório válido para salvar os arquivos KML.")
            return

        # Configurar a projeção para converter para metros
        project = partial(
            pyproj.Transformer.from_crs('EPSG:4326', 'EPSG:32723', always_xy=True).transform
        )

        with open(selected_file, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            next(reader)  # Pular o cabeçalho
            line_number = 1
            for row in reader:
                try:
                    wkt_polygon = row[3]
                    polygon = loads(wkt_polygon)
                    projected_polygon = transform(project, polygon)  # Transformar para a projeção em metros
                    area_m2 = projected_polygon.area  # Calcular a área do polígono em metros quadrados
                    area_hectares = area_m2 / 10000  # Converter a área para hectares
                    kml_filename = os.path.join(kml_directory, f"{line_number}_{os.path.basename(selected_file).replace('.csv', '')}_{area_hectares:.2f}_polygon.kml")
                    wkt_to_kml(wkt_polygon, kml_filename, opacity_color, area_hectares)
                    line_number += 1
                except Exception as e:
                    continue
        messagebox.showinfo("Sucesso", "Arquivos KML gerados com sucesso.")

    def on_generate_combined_kml():
        selected_file = selected_file_entry.get()
        if not selected_file or not os.path.exists(selected_file):
            messagebox.showerror("Erro", "Arquivo filtrado não selecionado ou não encontrado.")
            return

        # Obter a cor de opacidade do campo de entrada
        color = color_entry.get()
        if not color:
            messagebox.showerror("Erro", "Cor não fornecida.")
            return

        # Converter a cor para o formato ABGR exigido pelo KML
        opacity_color = "7d" + color[5:] + color[3:5] + color[1:3]

        generate_combined_kml(selected_file, opacity_color)
        messagebox.showinfo("Sucesso", "Arquivo KML combinado salvo com sucesso.")

    def select_color():
        color = askcolor(title="Escolha a cor de opacidade para a área destacada")[1]
        if color:
            color_entry.delete(0, tk.END)
            color_entry.insert(0, color)

    def select_kml_directory():
        directory = filedialog.askdirectory(initialdir='kml', title="Selecione o diretório para salvar os arquivos KML")
        if directory:
            kml_directory_entry.delete(0, tk.END)
            kml_directory_entry.insert(0, directory)

    # Janela principal
    root = tk.Tk()
    root.title("Filtragem de Glebas - Pronaf")

    # URL do Google Earth
    tk.Label(root, text="URL do Google Earth:").grid(row=0, column=0, sticky=tk.W)
    url_entry = tk.Entry(root, width=50)
    url_entry.grid(row=0, column=1, padx=10, pady=5)

    # Raio em metros
    tk.Label(root, text="Raio (em metros):").grid(row=1, column=0, sticky=tk.W)
    radius_entry = tk.Entry(root, width=20)
    radius_entry.grid(row=1, column=1, padx=10, pady=5)

    # Ano do arquivo
    tk.Label(root, text="Ano do arquivo (ex: 2024):").grid(row=2, column=0, sticky=tk.W)
    year_entry = tk.Entry(root, width=20)
    year_entry.grid(row=2, column=1, padx=10, pady=5)

    # Botão Filtrar
    filter_button = tk.Button(root, text="Filtrar", command=on_filter)
    filter_button.grid(row=3, column=1, pady=10, sticky=tk.E)

    # Seletor do arquivo filtrado
    tk.Label(root, text="Arquivo filtrado:").grid(row=4, column=0, sticky=tk.W)
    selected_file_entry = tk.Entry(root, width=50)
    selected_file_entry.grid(row=4, column=1, padx=10, pady=5)
    select_file_button = tk.Button(root, text="Selecionar", command=lambda: selected_file_entry.insert(0, filedialog.askopenfilename(initialdir='filtered', title="Selecione um arquivo filtrado", filetypes=[("CSV files", "*.csv")])))
    select_file_button.grid(row=4, column=2, padx=5, pady=5)

    # Seletor de cor
    tk.Label(root, text="Cor da área (opacidade):").grid(row=5, column=0, sticky=tk.W)
    color_entry = tk.Entry(root, width=20)
    color_entry.grid(row=5, column=1, padx=10, pady=5)
    color_button = tk.Button(root, text="Escolher Cor", command=select_color)
    color_button.grid(row=5, column=2, padx=5, pady=5)

    # Seletor do diretório para salvar KML
    tk.Label(root, text="Diretório para salvar KML:").grid(row=6, column=0, sticky=tk.W)
    kml_directory_entry = tk.Entry(root, width=50)
    kml_directory_entry.grid(row=6, column=1, padx=10, pady=5)
    select_kml_directory_button = tk.Button(root, text="Selecionar", command=select_kml_directory)
    select_kml_directory_button.grid(row=6, column=2, padx=5, pady=5)

    # Botão Gerar KML
    kml_button = tk.Button(root, text="Gerar KML", command=on_generate_kml)
    kml_button.grid(row=7, column=1, pady=10, sticky=tk.E)

    # Botão Gerar KML Combinado
    combined_kml_button = tk.Button(root, text="Gerar KML Combinado", command=on_generate_combined_kml)
    combined_kml_button.grid(row=8, column=1, pady=10, sticky=tk.E)

    root.mainloop()

if __name__ == "__main__":
    run_gui()