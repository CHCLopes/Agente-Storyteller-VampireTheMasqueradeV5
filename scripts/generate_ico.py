from PIL import Image, ImageDraw

def generate_vampire_ico():
    # Cria uma imagem RGBA (256x256)
    img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Fundo: círculo vermelho escuro com borda branca
    draw.ellipse([16, 16, 240, 240], fill=(139, 0, 0, 255), outline=(255, 255, 255, 255), width=4)
    
    # Capa preta gótica
    draw.polygon([(80, 110), (50, 150), (50, 200), (206, 200), (206, 150), (176, 110)], fill=(0, 0, 0, 200))
    
    # Rosto: elipse pergaminho
    draw.ellipse([78, 60, 178, 170], fill=(245, 240, 232, 255), outline=(0, 0, 0, 255), width=2)
    
    # Olhos vermelhos intensos
    draw.ellipse([98, 92, 114, 108], fill=(255, 0, 0, 255))
    draw.ellipse([142, 92, 158, 108], fill=(255, 0, 0, 255))
    
    # Pupilas pretas
    draw.ellipse([103, 97, 109, 103], fill=(0, 0, 0, 255))
    draw.ellipse([147, 97, 153, 103], fill=(0, 0, 0, 255))
    
    # Linha da boca gótica
    draw.arc([110, 115, 146, 135], start=0, end=180, fill=(0, 0, 0, 255), width=2)
    
    # Presa esquerda (triângulo branco)
    draw.polygon([(115, 126), (121, 126), (118, 138)], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
    
    # Presa direita (triângulo branco)
    draw.polygon([(135, 126), (141, 126), (138, 138)], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
    
    # Salva o arquivo ICO em múltiplos tamanhos padrão
    ico_path = 'vampire-icon.ico'
    img.save(ico_path, format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
    print(f"[✓] Ícone gerado com sucesso em: {ico_path}")

if __name__ == '__main__':
    generate_vampire_ico()
