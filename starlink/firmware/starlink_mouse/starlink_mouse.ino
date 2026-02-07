/*
 * Starlink Mouse Firmware v2.0
 * Arduino Leonardo - Advanced HID Mouse with Human-like Movement
 * 
 * Spoofed as: Logitech G Pro X Superlight
 * 
 * Features:
 * - Micro-jitter with velocity scaling
 * - Hand tremor simulation (8-12Hz)
 * - Micro-corrections after movements
 * - Natural timing variance
 * - Burst pattern simulation
 * - Deceleration smoothing
 * - Sub-pixel accumulation
 * 
 * Protocol:
 *   M,dx,dy    - Move mouse (relative, float)
 *   C,btn      - Click button (L/R/M)
 *   P,btn      - Press button (hold)
 *   R,btn      - Release button
 *   J,val      - Set jitter intensity (0-100)
 *   T,val      - Set tremor amplitude (0-100)
 *   E,0/1      - Enable/disable humanization
 *   ?          - Ping (returns OK)
 *   V          - Version
 *   S          - Status
 */

#include <Mouse.h>
#include "config.h"

// ============================================
// STATE VARIABLES
// ============================================

// Sub-pixel accumulator
float accum_x = 0.0f;
float accum_y = 0.0f;

// Previous movement for velocity calculation
float prev_dx = 0.0f;
float prev_dy = 0.0f;
float velocity = 0.0f;

// Humanization settings (runtime adjustable)
float jitter_intensity = JITTER_BASE_INTENSITY;
float tremor_amplitude = TREMOR_AMPLITUDE;
bool humanization_enabled = true;

// Timing state
unsigned long last_move_time = 0;
unsigned long next_timing_variance = 0;

// Tremor state
float tremor_phase = 0.0f;
float tremor_freq = 10.0f;
unsigned long last_tremor_update = 0;

// Burst pattern state
int burst_position = 0;
float burst_multiplier = 1.0f;

// Deceleration state
float smooth_velocity = 0.0f;
bool decelerating = false;

// Command parsing
char cmd_buffer[CMD_BUFFER_SIZE];
int cmd_index = 0;

// PRNG state (multiple seeds for different distributions)
unsigned long seed_main = 12345;
unsigned long seed_tremor = 67890;
unsigned long seed_timing = 11111;

// ============================================
// ADVANCED RANDOM NUMBER GENERATION
// ============================================

// XORShift128+ - better quality than basic xorshift
unsigned long xorshift_main() {
    unsigned long t = seed_main;
    t ^= t << 13;
    t ^= t >> 17;
    t ^= t << 5;
    seed_main = t;
    return t;
}

unsigned long xorshift_tremor() {
    unsigned long t = seed_tremor;
    t ^= t << 13;
    t ^= t >> 17;
    t ^= t << 5;
    seed_tremor = t;
    return t;
}

unsigned long xorshift_timing() {
    unsigned long t = seed_timing;
    t ^= t << 13;
    t ^= t >> 17;
    t ^= t << 5;
    seed_timing = t;
    return t;
}

// Random float [0, 1)
float rand_unit() {
    return (float)(xorshift_main() % 100000) / 100000.0f;
}

// Random float [-1, 1)
float rand_signed() {
    return (rand_unit() * 2.0f) - 1.0f;
}

// Box-Muller transform for true Gaussian distribution
float rand_gaussian() {
    float u1 = rand_unit();
    float u2 = rand_unit();
    
    // Avoid log(0)
    if (u1 < 0.0001f) u1 = 0.0001f;
    
    // Box-Muller transform
    float z = sqrt(-2.0f * log(u1)) * cos(6.28318f * u2);
    
    // Clamp to reasonable range
    if (z > 3.0f) z = 3.0f;
    if (z < -3.0f) z = -3.0f;
    
    return z;
}

// Perlin-like smooth noise for tremor
float smooth_noise(float phase) {
    int i0 = (int)phase;
    int i1 = i0 + 1;
    float t = phase - i0;
    
    // Smoothstep interpolation
    t = t * t * (3.0f - 2.0f * t);
    
    // Hash-based pseudo-random at integer points
    float n0 = (float)((i0 * 1103515245 + 12345) % 1000) / 500.0f - 1.0f;
    float n1 = (float)((i1 * 1103515245 + 12345) % 1000) / 500.0f - 1.0f;
    
    return n0 + t * (n1 - n0);
}

// ============================================
// HUMANIZATION FUNCTIONS
// ============================================

// Calculate current movement velocity
void update_velocity(float dx, float dy) {
    velocity = sqrt(dx * dx + dy * dy);
    
    // Smooth velocity for deceleration detection
    smooth_velocity = smooth_velocity * 0.7f + velocity * 0.3f;
    
    // Detect deceleration
    if (DECEL_SMOOTHING_ENABLED) {
        float velocity_ratio = (smooth_velocity > 0.1f) ? (velocity / smooth_velocity) : 1.0f;
        decelerating = (velocity_ratio < DECEL_THRESHOLD) && (velocity < 5.0f);
    }
    
    prev_dx = dx;
    prev_dy = dy;
}

// Velocity-scaled jitter intensity
float get_velocity_jitter_mult() {
    if (!VELOCITY_SCALING_ENABLED) return 1.0f;
    
    if (velocity < 3.0f) {
        // Very slow/stationary - minimal jitter
        return SLOW_MOVE_JITTER_MULT;
    } else if (velocity > VELOCITY_FAST_THRESHOLD) {
        // Fast movement - more natural shake
        return FAST_MOVE_JITTER_MULT;
    } else {
        // Interpolate
        float t = (velocity - 3.0f) / (VELOCITY_FAST_THRESHOLD - 3.0f);
        return SLOW_MOVE_JITTER_MULT + t * (FAST_MOVE_JITTER_MULT - SLOW_MOVE_JITTER_MULT);
    }
}

// Apply micro-jitter
void apply_jitter(float* dx, float* dy) {
    if (!JITTER_ENABLED || !humanization_enabled) return;
    if (jitter_intensity <= 0) return;
    
    // Probabilistic application
    if (rand_unit() > JITTER_PROBABILITY) return;
    
    // Velocity-scaled intensity
    float intensity = jitter_intensity * get_velocity_jitter_mult();
    
    // Gaussian-distributed jitter
    float jx = rand_gaussian() * intensity;
    float jy = rand_gaussian() * intensity;
    
    *dx += jx;
    *dy += jy;
}

// Apply hand tremor (low-frequency oscillation)
void apply_tremor(float* dx, float* dy) {
    if (!TREMOR_ENABLED || !humanization_enabled) return;
    if (tremor_amplitude <= 0) return;
    
    unsigned long now = micros();
    float dt = (now - last_tremor_update) / 1000000.0f;
    last_tremor_update = now;
    
    // Update tremor phase
    tremor_phase += tremor_freq * dt;
    if (tremor_phase > 1000.0f) tremor_phase -= 1000.0f;
    
    // Occasionally change tremor frequency (natural variation)
    if (rand_unit() < 0.01f) {
        tremor_freq = TREMOR_MIN_FREQ + rand_unit() * (TREMOR_MAX_FREQ - TREMOR_MIN_FREQ);
    }
    
    // Generate smooth tremor using multiple frequencies
    float tremor_x = smooth_noise(tremor_phase) * tremor_amplitude;
    float tremor_y = smooth_noise(tremor_phase + 100.0f) * tremor_amplitude;
    
    // Add subtle second harmonic
    tremor_x += smooth_noise(tremor_phase * 2.3f) * tremor_amplitude * 0.3f;
    tremor_y += smooth_noise(tremor_phase * 2.3f + 50.0f) * tremor_amplitude * 0.3f;
    
    *dx += tremor_x;
    *dy += tremor_y;
}

// Apply burst pattern (humans move in micro-bursts)
void apply_burst_pattern(float* dx, float* dy) {
    if (!BURST_PATTERN_ENABLED || !humanization_enabled) return;
    
    // Update burst position
    burst_position = (burst_position + 1) % BURST_CYCLE_LENGTH;
    
    // Calculate burst multiplier with smooth variation
    float phase = (float)burst_position / BURST_CYCLE_LENGTH;
    float wave = sin(phase * 6.28318f);
    
    burst_multiplier = 1.0f + wave * (BURST_VELOCITY_MAX - 1.0f) * 0.5f;
    burst_multiplier += rand_gaussian() * 0.02f;  // Add noise
    
    // Clamp
    if (burst_multiplier < BURST_VELOCITY_MIN) burst_multiplier = BURST_VELOCITY_MIN;
    if (burst_multiplier > BURST_VELOCITY_MAX) burst_multiplier = BURST_VELOCITY_MAX;
    
    *dx *= burst_multiplier;
    *dy *= burst_multiplier;
}

// Apply deceleration smoothing
void apply_decel_smoothing(float* dx, float* dy) {
    if (!DECEL_SMOOTHING_ENABLED || !humanization_enabled) return;
    if (!decelerating) return;
    
    // Smooth out the deceleration
    *dx *= DECEL_SMOOTH_FACTOR;
    *dy *= DECEL_SMOOTH_FACTOR;
}

// Calculate humanized timing delay
unsigned long calculate_timing_variance() {
    if (!TIMING_HUMANIZATION || !humanization_enabled) return 0;
    
    // Base interval for target poll rate
    unsigned long base_interval = 1000000UL / BASE_POLL_RATE;
    
    // Add Gaussian-distributed variance
    float variance = rand_gaussian() * (MAX_TIMING_VARIANCE_US - MIN_TIMING_VARIANCE_US) / 3.0f;
    long delay_us = (long)base_interval + (long)variance;
    
    // Occasional micro-pause (human hesitation)
    if (rand_unit() < MICRO_PAUSE_PROBABILITY) {
        delay_us += MICRO_PAUSE_MIN_US + (long)(rand_unit() * (MICRO_PAUSE_MAX_US - MICRO_PAUSE_MIN_US));
    }
    
    // Clamp to valid range
    if (delay_us < MIN_TIMING_VARIANCE_US) delay_us = MIN_TIMING_VARIANCE_US;
    if (delay_us > base_interval * 3) delay_us = base_interval * 3;
    
    return (unsigned long)delay_us;
}

// Check if micro-correction should be applied
bool should_micro_correct() {
    if (!MICRO_CORRECTIONS_ENABLED || !humanization_enabled) return false;
    return rand_unit() < MICRO_CORRECTION_PROB;
}

// ============================================
// MOUSE MOVEMENT
// ============================================

void execute_move(int mx, int my) {
    // Clamp to int8_t range (-128 to 127)
    if (mx > 127) mx = 127;
    if (mx < -128) mx = -128;
    if (my > 127) my = 127;
    if (my < -128) my = -128;
    
    if (mx != 0 || my != 0) {
        Mouse.move(mx, my, 0);
    }
}

void move_mouse(float dx, float dy) {
    // Update velocity tracking
    update_velocity(dx, dy);
    
    // Apply timing humanization
    unsigned long now = micros();
    if (now - last_move_time < next_timing_variance) {
        unsigned long wait = next_timing_variance - (now - last_move_time);
        if (wait > 0 && wait < 50000) {  // Sanity check
            delayMicroseconds(wait);
        }
    }
    
    // Store original for micro-correction
    float orig_dx = dx;
    float orig_dy = dy;
    
    // Apply humanization layers
    apply_burst_pattern(&dx, &dy);
    apply_decel_smoothing(&dx, &dy);
    apply_jitter(&dx, &dy);
    apply_tremor(&dx, &dy);
    
    // Sub-pixel accumulation
    if (SUBPIXEL_ENABLED) {
        accum_x += dx;
        accum_y += dy;
        
        int move_x = (int)accum_x;
        int move_y = (int)accum_y;
        
        accum_x -= move_x;
        accum_y -= move_y;
        
        execute_move(move_x, move_y);
    } else {
        execute_move((int)dx, (int)dy);
    }
    
    // Update timing
    last_move_time = micros();
    next_timing_variance = calculate_timing_variance();
    
    // Micro-correction (small adjustment after main movement)
    if (should_micro_correct() && (abs(orig_dx) > 2 || abs(orig_dy) > 2)) {
        unsigned long correction_delay = MICRO_CORRECTION_DELAY_MIN + 
            (unsigned long)(rand_unit() * (MICRO_CORRECTION_DELAY_MAX - MICRO_CORRECTION_DELAY_MIN));
        delayMicroseconds(correction_delay);
        
        // Small correction in random direction related to original movement
        float corr_x = orig_dx * MICRO_CORRECTION_MAGNITUDE * rand_gaussian();
        float corr_y = orig_dy * MICRO_CORRECTION_MAGNITUDE * rand_gaussian();
        
        accum_x += corr_x;
        accum_y += corr_y;
        
        int cx = (int)accum_x;
        int cy = (int)accum_y;
        accum_x -= cx;
        accum_y -= cy;
        
        execute_move(cx, cy);
    }
    
    #if DEBUG_OUTPUT
    Serial.print("M:");
    Serial.print(dx, 2);
    Serial.print(",");
    Serial.print(dy, 2);
    Serial.print(" v=");
    Serial.println(velocity, 1);
    #endif
}

// ============================================
// BUTTON FUNCTIONS
// ============================================

void click_button(char btn) {
    int button = MOUSE_LEFT;
    if (btn == 'R' || btn == 'r') button = MOUSE_RIGHT;
    else if (btn == 'M' || btn == 'm') button = MOUSE_MIDDLE;
    
    Mouse.press(button);
    
    // Realistic one-tap hold duration: 8-25ms
    // Fast clicking (like in FPS games) is very short!
    if (humanization_enabled) {
        // 8-25ms with small variance
        int hold_ms = 8 + (int)(rand_unit() * 17);
        delay(hold_ms);
    } else {
        delay(10);  // Fixed 10ms
    }
    
    Mouse.release(button);
}

void press_button(char btn) {
    int button = MOUSE_LEFT;
    if (btn == 'R' || btn == 'r') button = MOUSE_RIGHT;
    else if (btn == 'M' || btn == 'm') button = MOUSE_MIDDLE;
    
    Mouse.press(button);
}

void release_button(char btn) {
    int button = MOUSE_LEFT;
    if (btn == 'R' || btn == 'r') button = MOUSE_RIGHT;
    else if (btn == 'M' || btn == 'm') button = MOUSE_MIDDLE;
    
    Mouse.release(button);
}

// ============================================
// COMMAND PARSING
// ============================================

void process_command(char* cmd) {
    if (cmd[0] == '\0') return;
    
    char type = cmd[0];
    
    switch (type) {
        case 'M':
        case 'm': {
            // Move: M,dx,dy
            float dx = 0, dy = 0;
            char* p = cmd + 2;
            dx = atof(p);
            p = strchr(p, ',');
            if (p) dy = atof(p + 1);
            move_mouse(dx, dy);
            break;
        }
        
        case 'C':
        case 'c': {
            // Click: C,btn
            char btn = (cmd[2] != '\0') ? cmd[2] : 'L';
            click_button(btn);
            break;
        }
        
        case 'P':
        case 'p': {
            // Press: P,btn
            char btn = (cmd[2] != '\0') ? cmd[2] : 'L';
            press_button(btn);
            break;
        }
        
        case 'R':
        case 'r': {
            // Release: R,btn
            char btn = (cmd[2] != '\0') ? cmd[2] : 'L';
            release_button(btn);
            break;
        }
        
        case 'J':
        case 'j': {
            // Jitter intensity: J,val (0-100)
            int val = atoi(cmd + 2);
            jitter_intensity = JITTER_BASE_INTENSITY + (val / 100.0f) * (JITTER_MAX_INTENSITY - JITTER_BASE_INTENSITY);
            Serial.print("JITTER:");
            Serial.println(jitter_intensity, 3);
            break;
        }
        
        case 'T':
        case 't': {
            // Tremor amplitude: T,val (0-100)
            int val = atoi(cmd + 2);
            tremor_amplitude = (val / 100.0f) * TREMOR_AMPLITUDE * 2.0f;
            Serial.print("TREMOR:");
            Serial.println(tremor_amplitude, 3);
            break;
        }
        
        case 'E':
        case 'e': {
            // Enable/disable humanization: E,0 or E,1
            humanization_enabled = (cmd[2] == '1');
            Serial.print("HUMAN:");
            Serial.println(humanization_enabled ? "ON" : "OFF");
            break;
        }
        
        case 'H':
        case 'h': {
            // Set all humanization params: H,jitter,tremor,enabled
            char* p = cmd + 2;
            int j = atoi(p);
            p = strchr(p, ',');
            int t = p ? atoi(p + 1) : 50;
            p = p ? strchr(p + 1, ',') : NULL;
            int e = p ? atoi(p + 1) : 1;
            
            jitter_intensity = JITTER_BASE_INTENSITY + (j / 100.0f) * (JITTER_MAX_INTENSITY - JITTER_BASE_INTENSITY);
            tremor_amplitude = (t / 100.0f) * TREMOR_AMPLITUDE * 2.0f;
            humanization_enabled = (e == 1);
            
            Serial.println("OK:HUMAN_SET");
            break;
        }
        
        case '?': {
            // Ping
            Serial.println("OK:STARLINK");
            break;
        }
        
        case 'V':
        case 'v': {
            // Version
            Serial.println("VER:2.0.0");
            break;
        }
        
        case 'S':
        case 's': {
            // Status
            Serial.print("STATUS:j=");
            Serial.print(jitter_intensity, 2);
            Serial.print(",t=");
            Serial.print(tremor_amplitude, 2);
            Serial.print(",h=");
            Serial.print(humanization_enabled ? "1" : "0");
            Serial.print(",v=");
            Serial.println(velocity, 1);
            break;
        }
        
        case 'X':
        case 'x': {
            // Reset state
            accum_x = 0;
            accum_y = 0;
            velocity = 0;
            smooth_velocity = 0;
            burst_position = 0;
            Serial.println("OK:RESET");
            break;
        }
        
        default:
            #if DEBUG_OUTPUT
            Serial.print("UNK:");
            Serial.println(cmd);
            #endif
            break;
    }
}

// ============================================
// SETUP & LOOP
// ============================================

void setup() {
    // Initialize serial
    Serial.begin(SERIAL_BAUD);
    
    // Initialize mouse HID
    Mouse.begin();
    
    // Seed PRNGs with multiple entropy sources
    unsigned long entropy = analogRead(A0);
    entropy ^= analogRead(A1) << 4;
    entropy ^= analogRead(A2) << 8;
    entropy ^= micros();
    
    seed_main = entropy * 1103515245 + 12345;
    seed_tremor = entropy * 1664525 + 1013904223;
    seed_timing = entropy * 22695477 + 1;
    
    // Initialize timing
    last_move_time = micros();
    last_tremor_update = micros();
    next_timing_variance = calculate_timing_variance();
    
    // Initialize tremor frequency
    tremor_freq = TREMOR_MIN_FREQ + (rand_unit() * (TREMOR_MAX_FREQ - TREMOR_MIN_FREQ));
    
    #if DEBUG_OUTPUT
    Serial.println("STARLINK v2.0 READY");
    #endif
}

void loop() {
    // Process serial commands
    while (Serial.available() > 0) {
        char c = Serial.read();
        
        if (c == '\n' || c == '\r') {
            cmd_buffer[cmd_index] = '\0';
            if (cmd_index > 0) {
                process_command(cmd_buffer);
            }
            cmd_index = 0;
        } else if (cmd_index < CMD_BUFFER_SIZE - 1) {
            cmd_buffer[cmd_index++] = c;
        }
    }
}
