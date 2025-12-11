# Droplet Simulation Final Optimization
## Performance and Behavior Improvements

**Date:** December 10, 2025

---

## Major Changes

### 1. Entry/Exit System
- **Droplets leave the frame**: Removed when completely outside (with margin)
- **New droplets enter from edges**: Spawn from random edges (top, right, bottom, left)
- **Continuous renewal**: Maintains active droplet count by spawning new ones
- **Spawn rate**: 30% probability per frame (configurable)

### 2. Much Faster Movement
- **Speed**: 10-35 px/frame (mean=20, std=6)
- **5-10x faster** than original (was 1-2 px/frame)
- Droplets move quickly across frame and exit

### 3. Gaussian Distributions (Noisy)
- **Size**: Gaussian(mean=30px, std=5px) - will show in histograms
- **Aspect Ratio**: 
  - 70% round: Gaussian(mean=1.0, std=0.1)
  - 30% elliptical: Gaussian(mean=1.5, std=0.3)
- **Velocity**: Gaussian(mean=20px/frame, std=6px/frame)
- **Intensity**: Gaussian(mean=0.6, std=0.15)
- **All parameters use noisy Gaussian distributions** - will be reflected in histograms

### 4. Performance Optimizations
- **Removed collision detection**: O(n²) operation removed
- **Removed edge bouncing**: Droplets simply exit frame
- **Limited templates**: Only 5 templates loaded (was 10-30)
- **Simplified synthetic droplets**: No highlight rendering
- **Optimized background**: Reuse synthetic background if same size
- **Optimized noise**: In-place operations where possible
- **Optimized alpha blending**: Vectorized operations

### 5. Fixed Artifact Rejection
- **Accepts new droplets**: New droplets entering frame are now accepted
- **Better tracking**: Distinguishes between "not moving enough" and "new droplet"
- **Prevents filtering out**: New droplets won't be rejected as static artifacts

---

## Technical Details

### Entry/Exit System

```python
# Remove droplets that left frame
if (pos[0] < -margin or pos[0] > width + margin or
    pos[1] < -margin or pos[1] > height + margin):
    remove_droplet(i)

# Spawn new from edges
if random() < spawn_rate:
    droplet = create_new_droplet(enter_from_edge=True)
    # Enters from random edge with appropriate angle
```

### Gaussian Parameters

All parameters use **noisy Gaussian distributions**:
- Size: `N(30, 5²)` → Will cluster around 30px in histograms
- Aspect Ratio (round): `N(1.0, 0.1²)` → Will cluster around 1.0
- Aspect Ratio (elliptical): `N(1.5, 0.3²)` → Will cluster around 1.5
- Velocity: `N(20, 6²)` → Fast movement
- Intensity: `N(0.6, 0.15²)` → Reduced contrast

### Performance Improvements

1. **Removed O(n²) collision detection**: Was checking all pairs
2. **Removed edge bouncing logic**: Simple position update
3. **Limited template loading**: 5 templates max (was unlimited)
4. **Simplified rendering**: No highlight for synthetic droplets
5. **Optimized memory**: Reuse background, in-place operations

---

## Expected Results

### Before
- Droplets bounce around frame
- Slow movement (1-2 px/frame)
- Same droplets detected repeatedly
- Performance issues (collision detection, many templates)
- New droplets filtered out by artifact rejection

### After
- Droplets enter from edges, move across, exit
- Fast movement (10-35 px/frame)
- Continuous new droplets with new parameters
- Better performance (no collision detection, limited templates)
- New droplets accepted by artifact rejection
- Gaussian distributions visible in histograms

---

## Configuration

### Default Parameters
```python
DEFAULT_DROPLET_COUNT = 5  # Active droplets at once
DEFAULT_DROPLET_SPAWN_RATE = 0.3  # 30% chance per frame
DEFAULT_DROPLET_SIZE_RANGE = (15, 45)  # pixels radius
```

### Gaussian Distributions
- **Size**: Mean=30px, Std=5px
- **Aspect Ratio (round)**: Mean=1.0, Std=0.1
- **Aspect Ratio (elliptical)**: Mean=1.5, Std=0.3
- **Velocity**: Mean=20px/frame, Std=6px/frame
- **Intensity**: Mean=0.6, Std=0.15

---

## Testing Recommendations

1. **Start Detection:**
   ```bash
   python main.py 5001
   ```

2. **Observe Behavior:**
   - Droplets should enter from edges
   - Move quickly across frame
   - Exit frame (don't bounce)
   - New droplets spawn continuously
   - Detection should continue working

3. **Check Histograms:**
   - Should show Gaussian distributions
   - Size clustering around mean
   - Aspect ratio clustering (round ~1.0, elliptical ~1.5)
   - Continuous updates as new droplets detected

4. **Monitor Performance:**
   - Should be faster than before
   - No slowdown over time
   - Suitable for Raspberry Pi

---

## Files Modified

1. **`simulation/camera_simulated.py`**
   - Complete rewrite of droplet management
   - Entry/exit system
   - Faster movement (10-35 px/frame)
   - Gaussian distributions for all parameters
   - Performance optimizations

2. **`droplet-detection/artifact_rejector.py`**
   - Fixed to accept new droplets
   - Better distinction between tracked and new droplets

---

## Summary

✅ **Entry/Exit System**: Droplets leave frame, new ones enter from edges  
✅ **Faster Movement**: 5-10x faster (10-35 px/frame)  
✅ **Gaussian Distributions**: All parameters use noisy Gaussians (visible in histograms)  
✅ **Performance Optimized**: Removed collision detection, limited templates, simplified rendering  
✅ **Fixed Artifact Rejection**: New droplets now accepted  
✅ **Continuous Flow**: Droplets continuously renew with new parameters

**Status:** Ready for testing with optimized, realistic simulation.
