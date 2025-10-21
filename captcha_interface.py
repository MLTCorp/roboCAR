"""
Interface para resolução manual de CAPTCHA
Captura a imagem e exibe para o usuário resolver
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import io
import asyncio
from pathlib import Path


class CaptchaResolver:
    """Interface gráfica para resolver CAPTCHA manualmente"""

    def __init__(self):
        self.captcha_text = None
        self.root = None

    def _create_window(self, image_bytes: bytes):
        """Cria janela Tkinter com a imagem do CAPTCHA"""
        self.root = tk.Tk()
        self.root.title("Resolver CAPTCHA - CAR Downloader")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        # Centralizar janela
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.root.winfo_screenheight() // 2) - (400 // 2)
        self.root.geometry(f"500x400+{x}+{y}")

        # Título
        title_label = tk.Label(
            self.root,
            text="CAPTCHA Detectado",
            font=("Arial", 16, "bold"),
            fg="#2c3e50"
        )
        title_label.pack(pady=10)

        # Frame para imagem
        img_frame = tk.Frame(self.root, bg="#ecf0f1", relief=tk.SUNKEN, borderwidth=2)
        img_frame.pack(pady=10, padx=20)

        # Carregar e exibir imagem
        try:
            img = Image.open(io.BytesIO(image_bytes))
            # Redimensionar se necessário
            max_width, max_height = 450, 150
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            photo = ImageTk.PhotoImage(img)
            img_label = tk.Label(img_frame, image=photo, bg="#ecf0f1")
            img_label.image = photo  # Keep reference
            img_label.pack(padx=10, pady=10)
        except Exception as e:
            error_label = tk.Label(
                img_frame,
                text=f"Erro ao carregar imagem: {e}",
                fg="red"
            )
            error_label.pack(padx=10, pady=10)

        # Instrução
        instruction_label = tk.Label(
            self.root,
            text="Digite o texto da imagem acima:",
            font=("Arial", 11),
            fg="#34495e"
        )
        instruction_label.pack(pady=5)

        # Campo de entrada
        entry_var = tk.StringVar()
        entry = tk.Entry(
            self.root,
            textvariable=entry_var,
            font=("Arial", 14),
            width=30,
            justify='center'
        )
        entry.pack(pady=10)
        entry.focus()

        # Botão confirmar
        def on_submit():
            self.captcha_text = entry_var.get().strip()
            if self.captcha_text:
                self.root.quit()
                self.root.destroy()

        # Bind Enter key
        entry.bind('<Return>', lambda e: on_submit())

        submit_btn = tk.Button(
            self.root,
            text="Confirmar",
            command=on_submit,
            font=("Arial", 12, "bold"),
            bg="#27ae60",
            fg="white",
            width=15,
            height=2,
            cursor="hand2"
        )
        submit_btn.pack(pady=20)

        # Botão cancelar
        def on_cancel():
            self.captcha_text = None
            self.root.quit()
            self.root.destroy()

        cancel_btn = tk.Button(
            self.root,
            text="Cancelar",
            command=on_cancel,
            font=("Arial", 10),
            bg="#e74c3c",
            fg="white",
            width=10,
            cursor="hand2"
        )
        cancel_btn.pack()

        self.root.protocol("WM_DELETE_WINDOW", on_cancel)

    def resolve(self, image_bytes: bytes) -> str:
        """
        Abre janela para usuário resolver CAPTCHA

        Args:
            image_bytes: Bytes da imagem do CAPTCHA

        Returns:
            Texto digitado pelo usuário ou None se cancelar
        """
        self._create_window(image_bytes)
        self.root.mainloop()
        return self.captcha_text


def capturar_e_resolver_captcha_sync(image_bytes: bytes) -> str:
    """
    Versão síncrona para resolver CAPTCHA
    """
    resolver = CaptchaResolver()
    return resolver.resolve(image_bytes)


async def capturar_e_resolver_captcha(page, captcha_img_selector: str = 'img[alt*="captcha"], img[src*="captcha"], canvas') -> str:
    """
    Captura imagem do CAPTCHA da página e exibe para usuário resolver

    Args:
        page: Objeto Page do Playwright
        captcha_img_selector: Seletor CSS para encontrar a imagem do CAPTCHA

    Returns:
        Texto do CAPTCHA digitado pelo usuário
    """
    print("\n[CAPTCHA] Capturando imagem...")

    try:
        # Tentar encontrar elemento do CAPTCHA
        captcha_element = page.locator(captcha_img_selector).first

        # Esperar elemento estar visível (timeout maior)
        await captcha_element.wait_for(state='visible', timeout=10000)

        # Capturar screenshot do elemento
        image_bytes = await captcha_element.screenshot()

        print("[CAPTCHA] Imagem capturada! Abrindo interface...")

        # Rodar de forma síncrona (bloqueia mas é necessário para Tkinter)
        texto = capturar_e_resolver_captcha_sync(image_bytes)

        if texto:
            print(f"[CAPTCHA] Resolvido: '{texto}'")
            return texto
        else:
            print("[CAPTCHA] Cancelado pelo usuário")
            return None

    except Exception as e:
        print(f"[ERRO] Não foi possível capturar CAPTCHA: {e}")
        print("[FALLBACK] Tentando salvar screenshot da página inteira...")

        # Fallback: salvar screenshot da página
        try:
            screenshot_path = "./captcha_screenshot.png"
            await page.screenshot(path=screenshot_path)

            with open(screenshot_path, 'rb') as f:
                image_bytes = f.read()

            texto = capturar_e_resolver_captcha_sync(image_bytes)
            return texto

        except Exception as e2:
            print(f"[ERRO FALLBACK] {e2}")
            return None


# Teste standalone
async def teste_interface():
    """Testa a interface com uma imagem de exemplo"""
    print("Testando interface do CAPTCHA...")
    print("Criando imagem de teste...")

    # Criar imagem de teste
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new('RGB', (200, 60), color='white')
    draw = ImageDraw.Draw(img)

    try:
        # Tentar usar fonte do sistema
        font = ImageFont.truetype("arial.ttf", 30)
    except:
        font = ImageFont.load_default()

    draw.text((20, 15), "ABC123", fill='black', font=font)

    # Converter para bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()

    # Testar interface
    resolver = CaptchaResolver()
    texto = resolver.resolve(img_bytes)

    print(f"\nResultado: {texto}")


if __name__ == "__main__":
    # Teste standalone
    asyncio.run(teste_interface())
