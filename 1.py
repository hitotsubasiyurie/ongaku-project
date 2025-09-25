from PIL import Image
import os

def get_basic_image_info(image_path):
    """获取图像的基本信息"""
    try:
        with Image.open(image_path) as img:
            # 基本信息
            info = {
                'filename': os.path.basename(image_path),
                'format': img.format,
                'mode': img.mode,
                'resolution': img.size,
                'file_size': "{:.2f} MiB".format(os.path.getsize(image_path) /1024/1024)
            }
            # 尝试获取 EXIF 信息
            try:
                exif_data = img._getexif()
                if exif_data:
                    info['exif'] = exif_data
            except:
                info['exif'] = None
                
            return info
    except Exception as e:
        return f"Error: {e}"

# 使用示例
image_path = r"D:\移动云盘同步盘\ongaku-resource\このはな綺譚 [此花亭奇谭] [Konohana Kitan]\[LACA-9566] [2018-01-10] TVアニメ『このはな綺譚』おりじなるさうんどとらっく Disc 2 [LACA-9566] [27]\cover.jpg"
info = get_basic_image_info(image_path)
for key, value in info.items():
    print(f"{key}: {value}")

