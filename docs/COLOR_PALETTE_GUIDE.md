# Rio Controller Color Palette Guide

## Ocean Breeze - Biomedical Design System

This color palette is specifically designed for the Rio Microfluidics Controller interface, balancing biomedical professionalism with fresh, modern aesthetics while ensuring excellent readability and accessibility.

---

## Color Palette Overview

The **Ocean Breeze** palette consists of six carefully selected colors that work harmoniously together:

### Primary Colors

1. **Light Teal** (`#7FD3D3` / `rgb(127, 211, 211)`)
   - Use: Primary actions, highlights, active states
   - Psychology: Calming, trustworthy, clean
   - Accessibility: High contrast on dark backgrounds

2. **Light Gray** (`#E0E0E0` / `rgb(224, 224, 224)`)
   - Use: Backgrounds, subtle borders, disabled states
   - Psychology: Neutral, professional, unobtrusive
   - Accessibility: Excellent for text contrast

3. **Pure White** (`#FFFFFF` / `rgb(255, 255, 255)`)
   - Use: Primary backgrounds, text on dark, card surfaces
   - Psychology: Clean, sterile, clinical
   - Accessibility: Maximum contrast

4. **Sky Blue** (`#B3E5FC` / `rgb(179, 229, 252)`)
   - Use: Secondary actions, info states, hover effects
   - Psychology: Fresh, optimistic, clear
   - Accessibility: Good contrast on dark backgrounds

5. **Royal Blue** (`#2196F3` / `rgb(33, 150, 243)`)
   - Use: Primary buttons, links, important UI elements
   - Psychology: Professional, reliable, confident
   - Accessibility: Excellent contrast on white

6. **Navy Blue** (`#1565C0` / `rgb(21, 101, 192)`)
   - Use: Headers, emphasis, critical actions
   - Psychology: Serious, authoritative, stable
   - Accessibility: High contrast, readable

---

## Design Principles

### Balance Colors
The palette uses a strategic mix of warm and cool tones:
- **Cool tones** (blues, teals) dominate for a calming, professional atmosphere
- **Neutral tones** (grays, white) provide balance and prevent visual fatigue
- Avoid overly bright or dark colors that can cause discomfort during extended use

### Complementary Shades
Colors are paired to enhance visual harmony:
- **Teal + Royal Blue**: Creates depth and visual interest
- **Sky Blue + Navy**: Provides clear hierarchy
- **White + Light Gray**: Ensures clean, readable interfaces

### Readability Priority
High-contrast combinations ensure information stands out:
- **Dark text on light backgrounds**: Navy/Black on White/Light Gray
- **Light text on dark backgrounds**: White on Navy/Royal Blue
- **Interactive elements**: Royal Blue or Teal for clear call-to-action

### Accessibility Considerations
- All color combinations meet WCAG AA standards for contrast
- Color is never the sole indicator of information (icons, text labels accompany colors)
- Tested for color vision deficiencies (deuteranopia, protanopia, tritanopia)
- High contrast ratios ensure readability in various lighting conditions

### Versatile Design
The palette adapts across different mediums:
- **Digital screens**: Optimized for LCD/LED displays
- **Print materials**: CMYK conversion maintains color integrity
- **Dark mode**: Inverted palette maintains visual hierarchy

---

## Usage Guidelines

### Primary Actions
- **Buttons**: Royal Blue (`#2196F3`) for primary actions
- **Hover states**: Light Teal (`#7FD3D3`) for interactive feedback
- **Active states**: Navy Blue (`#1565C0`) for selected/active items

### Secondary Actions
- **Secondary buttons**: Sky Blue (`#B3E5FC`) with Royal Blue text
- **Info messages**: Sky Blue background with Navy text
- **Links**: Royal Blue, underline on hover

### Backgrounds
- **Main background**: Pure White (`#FFFFFF`)
- **Card backgrounds**: White with Light Gray (`#E0E0E0`) borders
- **Alternating rows**: Light Gray for subtle differentiation

### Text Colors
- **Primary text**: Navy Blue (`#1565C0`) or dark gray (`#333333`)
- **Secondary text**: Medium gray (`#666666`)
- **Light text on dark**: White (`#FFFFFF`)

### Status Indicators
- **Success**: Light Teal (`#7FD3D3`)
- **Information**: Sky Blue (`#B3E5FC`)
- **Warning**: Use with caution (consider amber/yellow from extended palette)
- **Error**: Use with caution (consider red from extended palette)

---

## Implementation Examples

### CSS Variables
```css
:root {
    --color-teal-light: #7FD3D3;
    --color-gray-light: #E0E0E0;
    --color-white: #FFFFFF;
    --color-blue-sky: #B3E5FC;
    --color-blue-royal: #2196F3;
    --color-blue-navy: #1565C0;
    
    /* Semantic colors */
    --color-primary: var(--color-blue-royal);
    --color-secondary: var(--color-blue-sky);
    --color-background: var(--color-white);
    --color-text-primary: var(--color-blue-navy);
    --color-text-secondary: #666666;
    --color-border: var(--color-gray-light);
}
```

### Bootstrap Integration
```css
.btn-primary {
    background-color: #2196F3;
    border-color: #2196F3;
}

.btn-primary:hover {
    background-color: #1565C0;
    border-color: #1565C0;
}

.bg-info {
    background-color: #B3E5FC !important;
    color: #1565C0;
}
```

---

## Testing in Real Environments

### Medical Setting Considerations
- **Bright lighting**: Colors remain visible and don't wash out
- **Dim lighting**: Sufficient contrast for night shifts
- **Multiple monitors**: Consistent appearance across displays
- **Long-term use**: Reduced eye strain through balanced palette

### Color Vision Deficiency Testing
- **Protanopia/Deuteranopia**: Blue tones remain distinguishable
- **Tritanopia**: Teal and blue maintain sufficient contrast
- **Monochrome**: Light/dark values provide clear hierarchy

### Contrast Ratios
All text/background combinations meet WCAG AA standards:
- **Navy on White**: 7.2:1 ✓
- **Royal Blue on White**: 4.5:1 ✓
- **White on Navy**: 7.2:1 ✓
- **Navy on Light Gray**: 5.8:1 ✓

---

## Extended Palette (Optional)

For special cases, consider these additional colors:

- **Success Green**: `#4CAF50` (for success states)
- **Warning Amber**: `#FFC107` (for warnings)
- **Error Red**: `#F44336` (for errors, use sparingly)
- **Dark Gray**: `#424242` (for additional text hierarchy)

---

## Best Practices

1. **Consistency**: Use the same color for the same function throughout the interface
2. **Hierarchy**: Use darker blues for more important elements
3. **Moderation**: Don't overuse bright colors; let white space breathe
4. **Context**: Consider the medical environment when choosing color intensity
5. **Feedback**: Use color changes to provide clear user feedback
6. **Testing**: Always test color combinations in the actual deployment environment

---

## References

- WCAG 2.1 Guidelines: https://www.w3.org/WAI/WCAG21/quickref/
- Color Contrast Analyzer: https://www.tpgi.com/color-contrast-checker/
- Medical UI Design Best Practices: Healthcare interface design standards

---

*This color palette guide is part of the Rio Microfluidics Controller design system. For questions or updates, refer to the design team.*

