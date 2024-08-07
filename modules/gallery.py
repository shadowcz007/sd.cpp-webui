"""sd.cpp-webui - Gallery module"""

import os
from PIL import Image

import gradio as gr

from modules.config import (
    txt2img_dir, img2img_dir
)


class GalleryManager:
    """Controls the gallery block"""
    def __init__(self, txt2img_gallery, img2img_gallery):
        self.page_num = 1
        self.ctrl = 0
        self.txt2img_dir = txt2img_gallery
        self.img2img_dir = img2img_gallery
        self.img_sel = ""

    def _get_img_dir(self):
        """Determines the directory based on the control value"""
        if self.ctrl == 0:
            return self.txt2img_dir
        if self.ctrl == 1:
            return self.img2img_dir
        return self.txt2img_dir

    def reload_gallery(self, ctrl_inp=None, fpage_num=1, subctrl=0):
        """Reloads the gallery block"""
        if ctrl_inp is not None:
            self.ctrl = int(ctrl_inp)
        img_dir = self._get_img_dir()
        imgs = []
        files = os.listdir(img_dir)
        image_files = [file for file in files
                       if file.endswith(('.jpg', '.png'))]
        start_index = (fpage_num * 16) - 16
        end_index = min(start_index + 16, len(image_files))
        for file_name in image_files[start_index:end_index]:
            image_path = os.path.join(img_dir, file_name)
            image = Image.open(image_path)
            imgs.append(image)
        self.page_num = fpage_num
        if subctrl == 0:
            return imgs, self.page_num, gr.Gallery(selected_index=None)
        return imgs

    def goto_gallery(self, fpage_num=1):
        """Loads a specific gallery page"""
        img_dir = self._get_img_dir()
        files = os.listdir(img_dir)
        total_imgs = len([file for file in files
                         if file.endswith(('.png', '.jpg'))])
        total_pages = (total_imgs + 15) // 16
        if fpage_num is None:
            fpage_num = 1
        self.page_num = min(fpage_num, total_pages)
        return self.reload_gallery(self.ctrl, self.page_num, subctrl=0)

    def next_page(self):
        """Moves to the next gallery page"""
        next_page_num = self.page_num + 1
        img_dir = self._get_img_dir()
        files = os.listdir(img_dir)
        total_imgs = len([file for file in files
                         if file.endswith(('.png', '.jpg'))])
        total_pages = (total_imgs + 15) // 16
        if next_page_num > total_pages:
            self.page_num = 1
        else:
            self.page_num = next_page_num
        imgs = self.reload_gallery(self.ctrl, self.page_num, subctrl=1)
        return imgs, self.page_num, gr.Gallery(selected_index=None)

    def prev_page(self):
        """Moves to the previous gallery page"""
        prev_page_num = self.page_num - 1
        img_dir = self._get_img_dir()
        files = os.listdir(img_dir)
        total_imgs = len([file for file in files
                         if file.endswith(('.png', '.jpg'))])
        total_pages = (total_imgs + 15) // 16
        if prev_page_num < 1:
            self.page_num = total_pages
        else:
            self.page_num = prev_page_num
        imgs = self.reload_gallery(self.ctrl, self.page_num, subctrl=1)
        return imgs, self.page_num, gr.Gallery(selected_index=None)

    def last_page(self):
        """Moves to the last gallery page"""
        img_dir = self._get_img_dir()
        files = os.listdir(img_dir)
        total_imgs = len([file for file in files
                         if file.endswith(('.png', '.jpg'))])
        total_pages = (total_imgs + 15) // 16
        self.page_num = total_pages
        imgs = self.reload_gallery(self.ctrl, self.page_num, subctrl=1)
        return imgs, self.page_num, gr.Gallery(selected_index=None)

    def img_info(self, sel_img: gr.SelectData):
        """Reads generation data from an image"""
        img_index = (self.page_num * 16) - 16 + sel_img.index
        img_dir = self._get_img_dir()
        file_paths = [os.path.join(img_dir, file)
                      for file in os.listdir(img_dir)
                      if os.path.isfile(os.path.join(img_dir, file)) and
                      file.lower().endswith(('.png', '.jpg'))]
        file_paths.sort(key=os.path.getctime)
        try:
            img_path = file_paths[img_index]
        except IndexError:
            return "Image index is out of range."
        self.img_sel = file_paths[img_index]
        if img_path.endswith(('.jpg', '.jpeg')):
            return extract_exif_from_jpg(img_path)
        if img_path.endswith('.png'):
            with open(img_path, 'rb') as file:
                if file.read(8) != b'\x89PNG\r\n\x1a\n':
                    return None
                while True:
                    length_chunk = file.read(4)
                    if not length_chunk:
                        return None
                    length = int.from_bytes(length_chunk, byteorder='big')
                    chunk_type = file.read(4).decode('utf-8')
                    png_block = file.read(length)
                    _ = file.read(4)
                    if chunk_type == 'tEXt':
                        _, value = png_block.split(b'\x00', 1)
                        png_exif = f"{value.decode('utf-8')}"
                        return f"PNG: tEXt\nPositive prompt: {png_exif}"
        return None

    def delete_img(self):
        """Deletes a selected image"""
        os.remove(self.img_sel)
        print(f"Deleted {self.img_sel}")
        return self.reload_gallery(None, self.page_num)


def extract_exif_from_jpg(img_path):
    """Extracts exif data from jpg"""
    img = Image.open(img_path)
    exif_data = img._getexif()

    if exif_data is not None:
        user_comment = exif_data.get(37510)  # 37510 = UserComment tag
        if user_comment:
            return f"JPG: Exif\nPositive prompt: "\
                   f"{user_comment.decode('utf-8')[9::2]}"

        return "JPG: No User Comment found."

    return "JPG: Exif\nNo EXIF data found."


def get_next_img(subctrl):
    """Creates a new image name"""
    if subctrl == 0:
        fimg_out = txt2img_dir
    elif subctrl == 1:
        fimg_out = img2img_dir
    else:
        fimg_out = txt2img_dir
    files = os.listdir(fimg_out)
    png_files = [file for file in files if file.endswith('.png') and
                 file[:-4].isdigit()]
    if not png_files:
        return "1.png"
    highest_number = max(int(file[:-4]) for file in png_files)
    next_number = highest_number + 1
    fnext_img = f"{next_number}.png"
    return fnext_img
