import asyncio
import random
from nicegui import ui, app

# ==========================================
# 1. Definisi Kelas Agen (Agent Definitions)
# ==========================================

class RoadSegmentAgent:
    """Agen Segmen Jalan: Memantau kepadatan dan kecepatan."""
    def __init__(self, s_id, name, length, capacity, initial_count, avg_speed, status_awal, coords_start, coords_end):
        self.id = s_id
        self.name = name
        self.length = length
        self.capacity = capacity
        self.vehicle_count = initial_count
        self.avg_speed = avg_speed
        self.status = status_awal
        # Koordinat untuk menggambar garis di peta (lat, lon)
        self.coords = [coords_start, coords_end]
        self.map_polyline = None # Placeholder untuk objek di peta

    def update_state(self):
        """Simulasi perubahan kondisi jalan (Data IoT/Sensor)."""
        # Densitas = Jumlah / Kapasitas
        density = self.vehicle_count / self.capacity

        # Logika sederhana: Kecepatan turun jika densitas naik
        if density > 0.85:
            self.status = "Macet Total"
            target_speed = random.uniform(5, 15)
            color = 'red'
        elif density > 0.65:
            self.status = "Padat"
            target_speed = random.uniform(15, 25)
            color = 'orange'
        else:
            self.status = "Lancar"
            target_speed = random.uniform(30, 45)
            color = 'green'
            
        # Pergerakan kecepatan menuju target agar smooth
        self.avg_speed = (self.avg_speed * 0.8) + (target_speed * 0.2)
        
        # Update visual warna garis jalan di peta
        if self.map_polyline:
             self.map_polyline.run_method('setStyle', {'color': color})

class TrafficLightAgent:
    """Agen Lampu Lalu Lintas: Mengatur durasi hijau berdasarkan antrean."""
    def __init__(self, tl_id, location_name, green_time, queue, status_awal, lat, lon):
        self.id = tl_id
        self.location = location_name
        self.green_time = green_time
        self.queue = queue
        self.status = status_awal
        self.lat = lat
        self.lon = lon
        self.map_marker = None # Placeholder untuk marker di peta

    def decide_action(self):
        """Logika Agentic: Adaptasi waktu hijau berdasarkan panjang antrean."""
        previous_green = self.green_time
        action_taken = "Tetap"

        # Thresholds (Ambang batas) untuk pengambilan keputusan
        CRITICAL_QUEUE = 120
        LOW_QUEUE = 40

        if self.queue >= CRITICAL_QUEUE:
            # Aksi: Perpanjang Waktu Hijau secara agresif
            self.green_time = min(90, self.green_time + 10) # Max 90 detik
            self.status = "Sangat Padat (Menguras)"
            action_taken = "++Hijau"
            marker_color = 'red'
        elif self.queue < LOW_QUEUE:
            # Aksi: Kurangi Waktu Hijau untuk efisiensi
            self.green_time = max(20, self.green_time - 5) # Min 20 detik
            self.status = "Lancar"
            action_taken = "--Hijau"
            marker_color = 'green'
        else:
            # Aksi: Pertahankan
            self.status = "Stabil"
            marker_color = 'yellow'

        # Simulasi Arus Keluar (Outflow):
        # Semakin lama hijau, semakin banyak kendaraan keluar antrean
        cars_cleared = int(self.green_time * random.uniform(0.5, 1.0))
        self.queue = max(0, self.queue - cars_cleared)

        # Update visual marker icon di peta (menggunakan workaround warna)
        if self.map_marker:
             # Trik sederhana di leaflet untuk mengubah warna marker standar
             hue = 0 if marker_color == 'red' else (120 if marker_color == 'green' else 60)
             self.map_marker.run_method('setIcon', {
                 'iconUrl': f'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-{marker_color}.png',
                 'shadowUrl': 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                 'iconSize': [25, 41], 'iconAnchor': [12, 41], 'popupAnchor': [1, -34], 'shadowSize': [41, 41]
             })


# ==========================================
# 2. Inisialisasi Data Awal (Sesuai Laporan)
# ==========================================

# Koordinat Aproksimasi di Yogyakarta untuk Visualisasi
COORD_TUGU = (-7.7829, 110.3670)
COORD_MALIOBORO_END = (-7.8003, 110.3652) # Dekat Ahmad Dahlan
COORD_GRAMEDIA = (-7.7836, 110.3777) # Sudirman/Colombo
COORD_GEJAYAN_AFFANDI = (-7.7754, 110.3916)
COORD_KALIURANG_RR = (-7.7521, 110.3919)
COORD_JOMBOR = (-7.7483, 110.3619) # Arah Magelang

# Inisialisasi Agen Segmen Jalan
roads = [
    RoadSegmentAgent("S1", "Jl. Malioboro", 900, 450, 380, 12, "Padat", COORD_TUGU, COORD_MALIOBORO_END),
    RoadSegmentAgent("S2", "Jl. Sudirman", 1200, 600, 210, 35, "Lancar", COORD_TUGU, COORD_GRAMEDIA),
    RoadSegmentAgent("S3", "Jl. Gejayan", 1500, 700, 520, 18, "Sangat Padat", COORD_GRAMEDIA, COORD_GEJAYAN_AFFANDI),
    # S4 & S5 disederhanakan koordinatnya untuk demo
    RoadSegmentAgent("S4", "Jl. Kaliurang", 2000, 900, 300, 40, "Lancar", COORD_GRAMEDIA, COORD_KALIURANG_RR),
    RoadSegmentAgent("S5", "Jl. Magelang", 2500, 1100, 850, 15, "Macet", COORD_TUGU, COORD_JOMBOR),
]

# Inisialisasi Agen Lampu Lalu Lintas
tl_agents = [
    TrafficLightAgent("TL1", "Malioboro – A. Dahlan", 45, 120, "Padat", *COORD_MALIOBORO_END),
    TrafficLightAgent("TL2", "Sudirman – Colombo", 35, 80, "Stabil", *COORD_GRAMEDIA),
    TrafficLightAgent("TL3", "Gejayan – Affandi", 50, 150, "Sangat Padat", *COORD_GEJAYAN_AFFANDI),
    TrafficLightAgent("TL4", "Kaliurang – Ringroad", 40, 90, "Lancar", *COORD_KALIURANG_RR),
]


# ==========================================
# 3. Setup Antarmuka (NiceGUI & Leaflet)
# ==========================================

# Container untuk data statistik di UI
road_data_container = None
tl_data_container = None

@ui.page('/')
def setup_ui():
    global road_data_container, tl_data_container
    
    # Header
    with ui.header().classes(replace='row items-center') as header:
        ui.icon('traffic', size='md')
        ui.label('Proyek AI Agentic: Manajemen Transportasi Perkotaan (Yogyakarta)').classes('text-h6')

    # Main Layout: Peta di Kiri, Panel Info di Kanan
    with ui.row().classes('w-full h-screen no-wrap'):
        
        # --- Peta OpenStreetMap ---
        with ui.card().classes('w-3/4 h-full p-0 gap-0'):
            # Inisialisasi Peta dipusatkan di tengah Jogja
            m = ui.leaflet(center=(-7.78, 110.38), zoom=13).classes('h-full w-full')
            
            # Tambahkan Segmen Jalan (Polyline) ke Peta
            for road in roads:
                # Warna awal oranye, akan diupdate oleh agen
                # Buat polyline dengan Leaflet API
                road.map_polyline = m.run_method('L.polyline', road.coords, {'color': 'orange', 'weight': 5, 'opacity': 0.7})

            # Tambahkan Agen TL (Marker) ke Peta
            for tl in tl_agents:
                tl.map_marker = m.marker(latlng=(tl.lat, tl.lon))

        # --- Panel Informasi Real-time ---
        with ui.card().classes('w-1/4 h-full scroll'):
            ui.label('Status Agen Real-time').classes('text-h6 q-mb-md')
            
            ui.markdown('---')
            ui.label('Agen Segmen Jalan (Sensor IoT)').classes('text-weight-bold')
            road_data_container = ui.column().classes('w-full') # Container untuk diisi nanti

            ui.markdown('---')
            ui.label('Agen Traffic Light (Keputusan AI)').classes('text-weight-bold')
            tl_data_container = ui.column().classes('w-full') # Container untuk diisi nanti
            
            with ui.card().classes('bg-grey-2 q-mt-lg'):
                 ui.markdown('> **Catatan Simulasi:**\n> Sistem berjalan dalam loop. Agen TL secara otomatis menyesuaikan waktu hijau berdasarkan panjang antrean yang disimulasikan. Warna di peta berubah sesuai status.')
    
    # Mulai background task untuk simulasi
    asyncio.create_task(simulation_loop())


# ==========================================
# 4. Logika Simulasi & Update UI Loop
# ==========================================

async def simulation_loop():
    """Loop utama yang berjalan di background untuk update state agen dan UI."""
    while True:
        # --- A. Update Agen Jalan (Simulasi Data Masuk) ---
        road_data_container.clear() # Bersihkan tampilan lama
        with road_data_container:
            for road in roads:
                # Simulasi fluktuasi acak jumlah kendaraan masuk ke jalan
                fluctuation = random.randint(-30, 50)
                road.vehicle_count = max(0, min(road.capacity + 200, road.vehicle_count + fluctuation))
                
                # Agen jalan menghitung status barunya
                road.update_state()
                
                # Update tampilan teks di panel kanan
                with ui.row().classes('w-full justify-between items-center q-py-xs border-b'):
                    ui.label(road.name).classes('text-weight-medium')
                    ui.label(f"{int(road.avg_speed)} km/j | {road.status}").classes('text-caption')

        # --- B. Update Agen TL (AI Decision Making) ---
        tl_data_container.clear()
        with tl_data_container:
            for tl in tl_agents:
                # Simulasi antrean bertambah (kendaraan datang dari jalan sebelumnya)
                # Dalam simulasi kompleks, ini diambil dari output RoadSegmentAgent terdekat
                incoming_traffic = random.randint(10, 60)
                tl.queue += incoming_traffic
                
                # Agen TL mengambil keputusan (AI Core Logic)
                tl.decide_action()
                
                # Update tampilan teks di panel kanan
                with ui.card().classes('w-full q-my-xs p-2 bg-blue-1'):
                    ui.label(f"{tl.id}: {tl.location}").classes('text-weight-bold text-caption')
                    with ui.row().classes('w-full justify-between'):
                         ui.label(f"Antrean: {tl.queue} unit").classes('text-caption text-red')
                         # Highlight keputusan AI
                         ui.label(f"Green Time: {tl.green_time}s").classes('text-caption text-weight-bolder bg-yellow-3 q-px-sm')

        # Tunggu 2 detik sebelum langkah simulasi berikutnya
        await asyncio.sleep(2)

# ==========================================
# 5. Main Program Execution
# ==========================================

# Jalankan server NiceGUI
ui.run(title='AI Transport Management Simulation', port=8080, favicon='🚦')