"""
Image icon processor that filters out background pixels by color range.
Sets background pixels within specified color bounds to black with alpha = 0.
Supports both RGB and HSV color spaces.
"""

import argparse
from PIL import Image
import sys
import colorsys


def parse_color(color_str: str) -> tuple[int, int , int]:
    """Parse color string in format 'R,G,B' to tuple (R, G, B)."""
    try:
        parts = color_str.split(',')
        if len(parts) != 3:
            raise ValueError(f"Color must have 3 components, got {len(parts)}")

        r, g, b = [int(x.strip()) for x in parts]

        if not all(0 <= val <= 255 for val in [r, g, b]):
            raise ValueError("Color values must be between 0 and 255")

        return (r, g, b)
    except Exception as e:
        raise ValueError(f"Invalid color format '{color_str}': {e}")


def parse_point(point_str: str) -> tuple[int, int]:
    """Parse point string in format 'x,y' to tuple (x, y)."""
    try:
        parts = point_str.split(',')
        if len(parts) != 2:
            raise ValueError(f"Point must have 2 coordinates, got {len(parts)}")
        return (int(parts[0].strip()), int(parts[1].strip()))
    except Exception as e:
        raise ValueError(f"Invalid point format '{point_str}': {e}")


def rgb_to_hsv_opencv(r, g, b):
    """
    Convert RGB (0-255) to HSV using OpenCV convention.

    Returns:
        tuple: (H, S, V) matching OpenCV's cv2.COLOR_BGR2HSV format
               H: 0-179 (maps 0-360° to 0-179, half-range for 8-bit storage)
               S: 0-255 (maps 0-100% saturation)
               V: 0-255 (maps 0-100% value/brightness)
    """
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return (int(h * 179), int(s * 255), int(v * 255))


def is_within_bounds(pixel, lower_bound, upper_bound, use_hsv=False):
    """
    Check if pixel color is within the specified bounds.

    Args:
        pixel: Pixel color tuple (R, G, B, A) or (R, G, B)
        lower_bound: Lower bound color tuple (3 values)
        upper_bound: Upper bound color tuple (3 values)
        use_hsv: If True, convert to HSV before comparison
    """
    r, g, b = pixel[:3]  # Only check RGB, ignore alpha if present

    if use_hsv:
        # Convert pixel to HSV (OpenCV convention: H=0-179, S=0-255, V=0-255)
        h, s, v = rgb_to_hsv_opencv(r, g, b)
        lh, ls, lv = lower_bound
        uh, us, uv = upper_bound

        return (lh <= h <= uh and
                ls <= s <= us and
                lv <= v <= uv)
    else:
        # RGB comparison
        lr, lg, lb = lower_bound
        ur, ug, ub = upper_bound

        return (lr <= r <= ur and
                lg <= g <= ug and
                lb <= b <= ub)


def find_connected_components(pixels, width: int, height: int) -> list[set[tuple[int, int]]]:
    """
    Find all connected components of foreground pixels (pixels with alpha > 0).

    Uses 4-connectivity (up, down, left, right neighbors).

    Returns:
        List of sets, where each set contains (x, y) coordinates of pixels in that component.
    """
    visited = set()
    components = []

    for start_y in range(height):
        for start_x in range(width):
            # Skip if already visited or is background (alpha == 0)
            if (start_x, start_y) in visited:
                continue
            if pixels[start_x, start_y][3] == 0:
                visited.add((start_x, start_y))
                continue

            # Found a new foreground pixel, flood fill to find the component
            component = set()
            stack = [(start_x, start_y)]
            visited.add((start_x, start_y))

            while stack:
                cx, cy = stack.pop()
                component.add((cx, cy))

                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        if (nx, ny) not in visited and pixels[nx, ny][3] > 0:
                            visited.add((nx, ny))
                            stack.append((nx, ny))

            components.append(component)

    return components


def keep_biggest_component(pixels, width: int, height: int) -> int:
    """
    Find connected components of foreground pixels and keep:
    1. The biggest connected component
    2. Any smaller components that are completely surrounded by the biggest component

    A smaller component is considered "surrounded" if it cannot reach the image boundary
    without passing through pixels of the biggest component. This preserves holes or
    enclosed regions within the main foreground object.

    Returns:
        Number of pixels removed (set to background).
    """
    components = find_connected_components(pixels, width, height)

    if len(components) <= 1:
        # No components or only one component, nothing to remove
        return 0

    # Find the biggest component
    biggest = max(components, key=len)

    # Create a set of all pixels NOT in the biggest component (both background and smaller components)
    biggest_set = set(biggest)

    # Flood fill from the image boundary through non-biggest pixels to find
    # all positions reachable from outside without crossing the biggest component
    reachable_from_boundary = set()
    stack = []

    # Add boundary pixels that are not part of the biggest component
    for x in range(width):
        for y in [0, height - 1]:
            if (x, y) not in biggest_set and (x, y) not in reachable_from_boundary:
                reachable_from_boundary.add((x, y))
                stack.append((x, y))
    for y in range(1, height - 1):
        for x in [0, width - 1]:
            if (x, y) not in biggest_set and (x, y) not in reachable_from_boundary:
                reachable_from_boundary.add((x, y))
                stack.append((x, y))

    # Flood fill through non-biggest pixels
    while stack:
        cx, cy = stack.pop()
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < width and 0 <= ny < height:
                if (nx, ny) not in biggest_set and (nx, ny) not in reachable_from_boundary:
                    reachable_from_boundary.add((nx, ny))
                    stack.append((nx, ny))

    # Remove smaller components that are reachable from the boundary (not surrounded)
    # Keep smaller components that are NOT reachable (completely surrounded by biggest)
    count = 0
    for component in components:
        if component is not biggest:
            # Check if any pixel in this component is reachable from the boundary
            # If so, the component is not surrounded and should be removed
            is_surrounded = not any(pixel in reachable_from_boundary for pixel in component)
            if not is_surrounded:
                for x, y in component:
                    pixels[x, y] = (0, 0, 0, 0)
                    count += 1

    return count


def process_image(
    input_path: str,
    lower_color: tuple[int, int, int],
    upper_color: tuple[int, int, int],
    inverse: bool,
    flood_fill: bool,
    manual_points: list[tuple[int, int]],
    output_path: str,
    use_hsv: bool = False,
    biggest_component: bool = False
):
    """
    Process image by setting background pixels within color bounds to black with alpha = 0.

    Args:
        input_path: Path to input image
        lower_color: Lower bound color tuple (R,G,B) or (H,S,V)
                     HSV uses OpenCV ranges: H=0-179, S=0-255, V=0-255
        upper_color: Upper bound color tuple (R,G,B) or (H,S,V)
                     HSV uses OpenCV ranges: H=0-179, S=0-255, V=0-255
        inverse: If True, remove pixels outside the color bounds
        flood_fill: If True, use flood fill from image boundary to remove background
        manual_points: List of (x, y) tuples to manually set as background/seeds
        output_path: Path to save processed image
        use_hsv: If True, use HSV color space for comparison (OpenCV convention)
        biggest_component: If True, keep only the biggest connected component of foreground
    """
    # Load image
    img = Image.open(input_path)

    # Convert to RGBA if not already (to support alpha channel)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # Get pixel data
    pixels = img.load()
    width, height = img.size
    assert width > 0 and height > 0, "Image must have positive dimensions"

    count = 0

    def is_background(p):
        within_bounds = is_within_bounds(p, lower_color, upper_color, use_hsv)
        return within_bounds != inverse # (not inverse and within_bounds) or (inverse and not within_bounds)

    if flood_fill:
        visited = set()
        stack = []

        # Add boundary pixels
        for x in range(width):
            for y in [0, height - 1]:
                if (x, y) not in visited and is_background(pixels[x, y]):
                    visited.add((x, y))
                    stack.append((x, y))
        for y in range(1, height-1):
            for x in [0, width - 1]:
                if (x, y) not in visited and is_background(pixels[x, y]):
                    visited.add((x, y))
                    stack.append((x, y))

        # Add manual points as seeds
        if manual_points:
            for x, y in manual_points:
                if 0 <= x < width and 0 <= y < height:
                    if (x, y) not in visited:
                        visited.add((x, y))
                        stack.append((x, y))

        while stack:
            cx, cy = stack.pop()
            pixels[cx, cy] = (0, 0, 0, 0)
            count += 1

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if (nx, ny) not in visited and is_background(pixels[nx, ny]):
                        visited.add((nx, ny))
                        stack.append((nx, ny))
    else:
        # Process manual points
        if manual_points:
            for x, y in manual_points:
                if 0 <= x < width and 0 <= y < height:
                    pixels[x, y] = (0, 0, 0, 0)
                    count += 1

        # Process each pixel
        for y in range(height):
            for x in range(width):
                if is_background(pixels[x, y]):
                    pixels[x, y] = (0, 0, 0, 0)  # Black with alpha = 0
                    count += 1

    # Keep only the biggest connected component if requested
    component_count = 0
    if biggest_component:
        component_count = keep_biggest_component(pixels, width, height)

    # Save processed image
    img.save(output_path, 'PNG')
    print(f"Processed image saved to {output_path}")
    print(f"Modified {count} pixels by color filtering (out of {width * height} total)")
    if biggest_component:
        print(f"Removed {component_count} pixels from smaller connected components")


def main():
    parser = argparse.ArgumentParser(
        description='Process image icon by removing background pixels within color bounds.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # RGB mode (default)
  %(prog)s input.png "255,0,0" "255,100,100" -o output.png
  %(prog)s icon.png "0,0,0" "50,50,50"

  # HSV mode (OpenCV ranges: H=0-179, S=0-255, V=0-255)
  %(prog)s input.png "0,100,100" "10,255,255" --hsv -f -o output.png
  %(prog)s icon.png "100,50,50" "130,255,255" --hsv  # Blue hue range

  # Keep only biggest connected component
  %(prog)s icon.png "0,0,0" "50,50,50" -b -o output.png
        '''
    )

    parser.add_argument('input', help='Path to input image')
    parser.add_argument('lower_color', help='Lower bound background color in format "R,G,B" or "H,S,V" (with --hsv)')
    parser.add_argument('upper_color', help='Upper bound background color in format "R,G,B" or "H,S,V" (with --hsv)')
    parser.add_argument('-i', '--inverse', action='store_true', help='inverse color range, defining the color outside of the bounds as background')
    parser.add_argument('--hsv', action='store_true',
                        help='Use HSV color space (OpenCV convention: H=0-179 for 0-360°, S=0-255, V=0-255)')
    parser.add_argument('-f', '--flood-fill', action='store_true', help='Use flood fill from image boundary to remove background')
    parser.add_argument('-b', '--biggest-component', action='store_true',
                        help='Keep the biggest connected component and any smaller components completely surrounded by it as the only foreground')
    parser.add_argument('-p', '--points', nargs='+', help='Manually add a point "x,y" to be set as background (and used as seed for flood fill)')
    parser.add_argument('-o', '--output', default='output.png',
                        help='Output path (default: output.png)')

    args = parser.parse_args()

    # Parse color values
    try:
        lower = parse_color(args.lower_color)
        upper = parse_color(args.upper_color)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    manual_points = []
    if args.points:
        try:
            for p in args.points:
                manual_points.append(parse_point(p))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Process the image
    process_image(args.input, lower, upper, args.inverse, args.flood_fill, manual_points, args.output, args.hsv, args.biggest_component)


if __name__ == '__main__':
    main()
