# 使用Ubuntu 22.04作为基础镜像
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:0
ENV QT_X11_NO_MITSHM=1
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    # GUI相关依赖
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    # Qt5相关依赖
    libqt5gui5 \
    libqt5core5a \
    libqt5widgets5 \
    qt5-gtk-platformtheme \
    # OpenCV相关依赖
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # HDF5相关依赖
    libhdf5-dev \
    pkg-config \
    # 字体支持
    fonts-wqy-microhei \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# 创建工作目录
WORKDIR /app

# 复制requirements.txt并安装Python依赖
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt 

# 复制应用程序文件
COPY . .

# 确保字体文件权限正确
RUN chmod -R 755 fonts/

# 创建非root用户
RUN useradd -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 默认命令
CMD ["python3", "main.py"]
