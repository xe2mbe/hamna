-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Create event types catalog
CREATE TABLE IF NOT EXISTS eventos_type (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);

-- Create section types catalog
CREATE TABLE IF NOT EXISTS tipos_seccion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);

-- Create events table
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tipo_evento_id INTEGER NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tipo_evento_id) REFERENCES eventos_type(id) ON DELETE CASCADE
);

-- Create sections table
CREATE TABLE IF NOT EXISTS secciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tipo_seccion_id INTEGER NOT NULL,
    evento_id INTEGER NOT NULL,
    duracion_seg REAL,
    metadata TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP,
    FOREIGN KEY (tipo_seccion_id) REFERENCES tipos_seccion(id) ON DELETE CASCADE,
    FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE
);

-- Create TTS section details
CREATE TABLE IF NOT EXISTS seccion_tts (
    seccion_id INTEGER PRIMARY KEY,
    texto TEXT NOT NULL,
    archivo TEXT,
    duracion_seg REAL,
    idioma TEXT,
    voz TEXT,
    FOREIGN KEY (seccion_id) REFERENCES secciones(id) ON DELETE CASCADE
);

-- Create Audio section details
CREATE TABLE IF NOT EXISTS seccion_audio (
    seccion_id INTEGER PRIMARY KEY,
    archivo TEXT NOT NULL,
    duracion_seg REAL,
    formato TEXT,
    bitrate INTEGER,
    FOREIGN KEY (seccion_id) REFERENCES secciones(id) ON DELETE CASCADE
);

-- Create Sound section details
CREATE TABLE IF NOT EXISTS seccion_sonido (
    seccion_id INTEGER PRIMARY KEY,
    archivo TEXT NOT NULL,
    duracion_seg REAL CHECK (duracion_seg <= 3.0),
    efecto TEXT,
    FOREIGN KEY (seccion_id) REFERENCES secciones(id) ON DELETE CASCADE
);

-- Create schedules table
CREATE TABLE IF NOT EXISTS programaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    evento_id INTEGER,
    tipo TEXT NOT NULL CHECK (tipo IN ('única', 'recurrente')),
    activa INTEGER DEFAULT 1 CHECK (activa IN (0, 1)),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE SET NULL
);

-- Create schedule times
CREATE TABLE IF NOT EXISTS programacion_horarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    programacion_id INTEGER NOT NULL,
    dia_semana TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    hora_fin TEXT,
    intervalo_min INTEGER,
    unica_fecha TIMESTAMP,
    FOREIGN KEY (programacion_id) REFERENCES programaciones(id) ON DELETE CASCADE
);

-- Create schedule details
CREATE TABLE IF NOT EXISTS programacion_detalle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    programacion_id INTEGER NOT NULL,
    seccion_id INTEGER NOT NULL,
    orden INTEGER NOT NULL,
    retraso_seg INTEGER DEFAULT 0,
    FOREIGN KEY (programacion_id) REFERENCES programaciones(id) ON DELETE CASCADE,
    FOREIGN KEY (seccion_id) REFERENCES secciones(id) ON DELETE CASCADE,
    UNIQUE(programacion_id, seccion_id, orden)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_secciones_evento_id ON secciones(evento_id);
CREATE INDEX IF NOT EXISTS idx_programaciones_evento_id ON programaciones(evento_id);
CREATE INDEX IF NOT EXISTS idx_programacion_horarios_programacion_id ON programacion_horarios(programacion_id);
CREATE INDEX IF NOT EXISTS idx_programacion_detalle_programacion_id ON programacion_detalle(programacion_id);
CREATE INDEX IF NOT EXISTS idx_programacion_detalle_seccion_id ON programacion_detalle(seccion_id);

-- Insert initial data
INSERT OR IGNORE INTO eventos_type (nombre) VALUES 
    ('Boletín'),
    ('Activación'),
    ('Simulación');

INSERT OR IGNORE INTO tipos_seccion (nombre) VALUES 
    ('TTS'),
    ('Audio'),
    ('Sonido');

-- Enable WAL mode for better concurrency
PRAGMA journal_mode=WAL;
