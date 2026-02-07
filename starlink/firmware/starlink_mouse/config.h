/*
 * Starlink Mouse - Configuration
 * Advanced humanization for undetectable mouse movement
 * 
 * Spoofed as: Logitech G Pro X Superlight
 */

#ifndef CONFIG_H
#define CONFIG_H

// ============================================
// DEVICE SPOOFING (set in boards.txt)
// ============================================
// VID: 0x046D (Logitech)
// PID: 0xC094 (G Pro X Superlight)
// Product: "PRO X SUPERLIGHT"
// Manufacturer: "Logitech"

// ============================================
// MICRO-JITTER SETTINGS
// ============================================

#define JITTER_ENABLED true

// Base jitter intensity (pixels) - very subtle
// Real mice have sensor noise of ~0.1-0.5px
#define JITTER_BASE_INTENSITY 0.3f

// Maximum jitter intensity at high velocity
#define JITTER_MAX_INTENSITY 0.8f

// Jitter probability per movement
#define JITTER_PROBABILITY 0.65f

// ============================================
// HAND TREMOR SIMULATION
// ============================================

// Simulates natural hand micro-tremor (8-12 Hz in humans)
#define TREMOR_ENABLED true

// Tremor frequency range (Hz)
#define TREMOR_MIN_FREQ 8.0f
#define TREMOR_MAX_FREQ 12.0f

// Tremor amplitude (pixels) - very subtle
#define TREMOR_AMPLITUDE 0.15f

// ============================================
// VELOCITY-DEPENDENT BEHAVIOR
// ============================================

// Faster movements = more natural variation
#define VELOCITY_SCALING_ENABLED true

// Velocity threshold for "fast" movement (pixels/frame)
#define VELOCITY_FAST_THRESHOLD 15.0f

// Slow movement jitter multiplier (steadier hand)
#define SLOW_MOVE_JITTER_MULT 0.5f

// Fast movement jitter multiplier (more shake)
#define FAST_MOVE_JITTER_MULT 1.5f

// ============================================
// MICRO-CORRECTIONS
// ============================================

// Simulates human micro-adjustments after main movement
#define MICRO_CORRECTIONS_ENABLED true

// Probability of adding a micro-correction
#define MICRO_CORRECTION_PROB 0.15f

// Micro-correction delay range (microseconds)
#define MICRO_CORRECTION_DELAY_MIN 2000
#define MICRO_CORRECTION_DELAY_MAX 8000

// Micro-correction magnitude (fraction of original move)
#define MICRO_CORRECTION_MAGNITUDE 0.08f

// ============================================
// TIMING HUMANIZATION
// ============================================

#define TIMING_HUMANIZATION true

// Base polling rate (Hz) - G Pro X Superlight is 1000Hz
#define BASE_POLL_RATE 1000

// Timing variance range (microseconds)
// Real USB polling has ~50-200µs jitter
#define MIN_TIMING_VARIANCE_US 50
#define MAX_TIMING_VARIANCE_US 250

// Occasional micro-pause probability (human hesitation)
#define MICRO_PAUSE_PROBABILITY 0.02f
#define MICRO_PAUSE_MIN_US 500
#define MICRO_PAUSE_MAX_US 3000

// ============================================
// MOVEMENT SMOOTHING
// ============================================

// Natural deceleration at end of movements
#define DECEL_SMOOTHING_ENABLED true

// Deceleration detection threshold (velocity drop)
#define DECEL_THRESHOLD 0.3f

// Smoothing factor for deceleration (0-1)
#define DECEL_SMOOTH_FACTOR 0.7f

// ============================================
// BURST PATTERN SIMULATION
// ============================================

// Humans move in micro-bursts, not constant velocity
#define BURST_PATTERN_ENABLED true

// Burst cycle length (movements)
#define BURST_CYCLE_LENGTH 8

// Velocity variation within burst (multiplier range)
#define BURST_VELOCITY_MIN 0.92f
#define BURST_VELOCITY_MAX 1.08f

// ============================================
// SUB-PIXEL ACCUMULATION
// ============================================

#define SUBPIXEL_ENABLED true

// ============================================
// SERIAL SETTINGS
// ============================================

#define SERIAL_BAUD 115200
#define CMD_BUFFER_SIZE 64

// ============================================
// DEBUG (DISABLE FOR PRODUCTION!)
// ============================================

#define DEBUG_OUTPUT false

#endif // CONFIG_H
