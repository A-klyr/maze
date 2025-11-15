# maze_data.py
import random

def generate_maze(width=61, height=61):
    """
    Generate maze solvable menggunakan recursive backtracking.
    1 = dinding, 0 = jalan, S = start, E = end
    """

    # Pastikan ukuran ganjil biar struktur maze simetris
    if width % 2 == 0: width += 1
    if height % 2 == 0: height += 1

    # Buat semua sel menjadi dinding
    maze = [["1" for _ in range(width)] for _ in range(height)]

    def carve(x, y):
        # Tandai sel saat ini sebagai jalan
        maze[y][x] = "0"
        
        # Arah: kanan, kiri, bawah, atas (bergerak 2 sel sekaligus)
        directions = [(2, 0), (-2, 0), (0, 2), (0, -2)]
        random.shuffle(directions)
        
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            # Perbaikan: ubah kondisi boundary dari "1 <" menjadi "0 <"
            if 0 < nx < width - 1 and 0 < ny < height - 1 and maze[ny][nx] == "1":
                # Buka jalan antara sel saat ini dan sel tujuan
                maze[y + dy // 2][x + dx // 2] = "0"
                # Rekursif ke sel berikutnya
                carve(nx, ny)

    # Titik awal dan akhir (koordinat jalan)
    start_x, start_y = 1, 1
    end_x, end_y = width - 2, height - 2

    # Mulai carving dari titik awal
    carve(start_x, start_y)

    # Tandai start dan end setelah maze jadi
    maze[start_y][start_x] = "S"
    maze[end_y][end_x] = "E"

    # Pastikan end cell adalah jalan (bukan dinding)
    if maze[end_y][end_x] == "1":
        maze[end_y][end_x] = "E"

    return ["".join(row) for row in maze]

# Default ukuran cell (digunakan di main.py)
CELL_SIZE = 10