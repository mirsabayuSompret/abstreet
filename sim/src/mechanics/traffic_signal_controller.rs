// File: src/traffic_agent.rs

use map_model::{IntersectionID, LaneID, Map, TurnPriority};
use sim::{CarID, Sim, VehicleType};
use std::collections::HashMap;
use std::time::Duration;

// ---------------------------------------------------------
// BAGIAN 1: MODEL MATEMATIKA & VARIABEL KEADAAN (Soal 2)
// ---------------------------------------------------------

/// Struct untuk menampung Data Sensor dari CCTV/IoT
#[derive(Debug, Clone)]
struct SensorData {
    queue_length: usize,        // w_j(t): Panjang antrean
    avg_speed: f64,             // v_i(t): Kecepatan rata-rata (km/j)
    flow_rate: f64,             // q_i(t): Arus kendaraan
    waiting_time_integral: f64, // Integral waktu tunggu
}

impl SensorData {
    fn new() -> Self {
        SensorData { queue_length: 0, avg_speed: 0.0, flow_rate: 0.0, waiting_time_integral: 0.0 }
    }
}

// ---------------------------------------------------------
// BAGIAN 2: DESAIN AGEN (Soal 3)
// ---------------------------------------------------------

/// 3.1 Agen Lampu Lalu Lintas (Traffic Light Agent - TLA)
/// Bertugas mengontrol durasi fase di persimpangan (Sinyal Merah/Hijau)
struct TrafficLightAgent {
    id: IntersectionID,
    location_name: String, // Misal: "TL3 Gejayan"
    current_green_duration: Duration,
    neighbor_ids: Vec<IntersectionID>, // Untuk koordinasi (Green Wave)
    alpha: f64, // Faktor pembobot (Soal 2.4)
}

impl TrafficLightAgent {
    pub fn new(id: IntersectionID, name: &str, neighbors: Vec<IntersectionID>) -> Self {
        TrafficLightAgent {
            id,
            location_name: name.to_string(),
            current_green_duration: Duration::from_secs(30), // Default fixed-time
            neighbor_ids: neighbors,
            alpha: 0.5,
        }
    }

    /// Soal 2.4: Menghitung Reward Function
    /// R_t = - (Sum(w_j(t)) + alpha * Delta v)
    fn calculate_reward(&self, current_queue: usize, prev_speed: f64, curr_speed: f64) -> f64 {
        let queue_penalty = current_queue as f64;
        let delta_v = curr_speed - prev_speed; // Bonus jika kecepatan naik
        
        // Reward negatif karena kita ingin meminimalkan penalty
        -(queue_penalty + (self.alpha * delta_v))
    }

    /// Soal 5.1: Logika Keputusan (Decision Making)
    /// Menggantikan logika DQN penuh dengan Heuristic Threshold untuk simulasi ini
    pub fn decide_next_phase(&mut self, sensor: &SensorData, map: &Map) -> String {
        let queue_threshold_heavy = 100; // Kondisi "Sangat Padat"
        let queue_threshold_light = 20;

        // Logika Adaptif
        if sensor.queue_length > queue_threshold_heavy {
            // Action: Extend Green
            self.current_green_duration += Duration::from_secs(10);
            return format!("EXTEND_GREEN (Antrean: {}, Reward Prediksi: Buruk)", sensor.queue_length);
        } else if sensor.queue_length < queue_threshold_light {
            // Action: Shorten Green to prevent waste
            self.current_green_duration = std::cmp::max(Duration::from_secs(10), self.current_green_duration - Duration::from_secs(5));
            return format!("SHORTEN_GREEN (Antrean: {}, Optimasi Arus)", sensor.queue_length);
        }

        "MAINTAIN_PHASE".to_string()
    }
}

/// 3.2 Agen Segmen Jalan (Road Segment Agent - RSA)
/// Memantau kesehatan segmen jalan (S1 - S5)
struct RoadSegmentAgent {
    lane_id: LaneID,
    name: String, // Misal: "S3 Jl. Gejayan"
    capacity: usize,
}

impl RoadSegmentAgent {
    /// Menghitung Saturation Degree (DS)
    /// Jika DS > 0.85, kirim sinyal broadcast congestion
    pub fn monitor_status(&self, sim: &Sim) -> (f64, bool) {
        // Mengambil data real-time dari engine A/B Street
        // queue count adalah pendekatan untuk 'Volume' saat ini
        let current_volume = sim.get_analytics().queue_length(self.lane_id); 
        let ds = current_volume as f64 / self.capacity as f64;
        
        let is_congested = ds > 0.85;
        (ds, is_congested)
    }
}

// ---------------------------------------------------------
// BAGIAN 3: SISTEM KOORDINASI & UTAMA (Soal 4 & 6)
// ---------------------------------------------------------

pub struct UrbanTrafficManager {
    tla_agents: HashMap<IntersectionID, TrafficLightAgent>,
    rsa_agents: Vec<RoadSegmentAgent>,
    map: Map,
}

impl UrbanTrafficManager {
    pub fn new(map: Map) -> Self {
        UrbanTrafficManager {
            tla_agents: HashMap::new(),
            rsa_agents: Vec::new(),
            map,
        }
    }

    // Fungsi inisialisasi agen berdasarkan Laporan
    pub fn initialize_agents(&mut self) {
        // Mapping ID (Biasanya diambil dari file OSM map)
        // Disini kita gunakan dummy ID untuk demonstrasi
        let id_tl1 = IntersectionID(1); // Malioboro
        let id_tl3 = IntersectionID(3); // Gejayan

        // Inisialisasi TL3 (Gejayan)
        let tl3 = TrafficLightAgent::new(
            id_tl3, 
            "TL3 Gejayan", 
            vec![id_tl1] // Tetangga
        );
        self.tla_agents.insert(id_tl3, tl3);

        // Inisialisasi Segmen Jalan S3
        let s3 = RoadSegmentAgent {
            lane_id: LaneID(301), // ID dummy
            name: "S3 Jl. Gejayan".to_string(),
            capacity: 700,
        };
        self.rsa_agents.push(s3);
    }

    /// Loop Utama Simulasi (Tick-based)
    pub fn step(&mut self, sim: &mut Sim) {
        // 1. Update Sensing dari Road Agents (RSA)
        for rsa in &self.rsa_agents {
            let (ds, congested) = rsa.monitor_status(sim);
            if congested {
                println!("[ALERT] {} Macet Parah! DS: {:.2}. Broadcasting signal...", rsa.name, ds);
                // Di sistem nyata: Kirim pesan MQTT ke Agen Kendaraan untuk Rerouting (Soal 4.3)
            }
        }

        // 2. Update Decision dari Traffic Light Agents (TLA)
        // Kita butuh mutable borrow terpisah atau iterasi keys
        let agent_ids: Vec<IntersectionID> = self.tla_agents.keys().cloned().collect();

        for id in agent_ids {
            // Simulasi mengambil data sensor antrean dari Sim
            // Di A/B Street asli: sim.get_analytics()...
            let sensor_mock = SensorData {
                queue_length: 150, // Hardcoded contoh data awal laporan (Sangat Padat)
                avg_speed: 18.0,
                flow_rate: 1200.0,
                waiting_time_integral: 5000.0,
            };

            if let Some(agent) = self.tla_agents.get_mut(&id) {
                // Agent berpikir
                let action = agent.decide_next_phase(&sensor_mock, &self.map);
                
                // Agent bertindak
                // Di implementasi nyata: apply_duration_override(agent.current_green_duration)
                println!("[AGENT {}] Action: {} -> Durasi Hijau Baru: {:?}", 
                    agent.location_name, action, agent.current_green_duration);
                
                // Kalkulasi Reward untuk pembelajaran (RL)
                let reward = agent.calculate_reward(sensor_mock.queue_length, 18.0, 20.0);
                println!("          Current Reward (RL): {:.2}", reward);
            }
        }
    }
}

// ---------------------------------------------------------
// ENTRY POINT (Soal 6 - Link Code)
// ---------------------------------------------------------
fn main() {
    println!("--- Memulai Sistem AI Agentic Manajemen Transportasi ---");
    
    // 1. Load Map (Di A/B Street, ini memuat file .bin map)
    // let map = Map::load_synchronously("maps/yogyakarta.bin".to_string(), ...);
    let map = Map::blank(); // Placeholder
    
    // 2. Setup Manager
    let mut manager = UrbanTrafficManager::new(map);
    manager.initialize_agents();

    // 3. Setup Simulasi A/B Street (Mocking)
    // let mut sim = Sim::new(&map, ...);
    // Placeholder struct untuk kompilasi
    struct MockSim;
    impl MockSim {
        fn get_analytics(&self) -> MockAnalytics { MockAnalytics }
    }
    struct MockAnalytics;
    impl MockAnalytics {
        fn queue_length(&self, _id: LaneID) -> usize { 550 } // Contoh volume S3
    }
    let mut sim = MockSim; // Seharusnya object Sim asli

    // 4. Jalankan 1 Step Simulasi
    // Di aplikasi nyata, ini ada dalam loop `timer`
    manager.step(&mut unsafe { std::mem::transmute(&mut sim) }); // Unsafe hanya karena mocking struct
    
    println!("--- Simulasi Selesai ---");
}