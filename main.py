#!/usr/bin/env python3
"""Enhanced CLI wrapper for the unifero tools.

Supports both modern CLI argument parsing and legacy JSON input for backward compatibility.
Provides search and docs modes with proper error handling and user-friendly output.
"""

import sys
import json
import os
import argparse
import logging
from typing import Optional, Dict, Any

from tools.unifero import UniferoTool

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Collection of example inputs for help/examples
EXAMPLE_INPUTS = {
    "search_minimal": {"mode": "search", "query": "Next.js routing"},
    "search_full": {"mode": "search", "query": "Next.js routing", "limit": 3, "snippet_len": 150, "content_len": 2000},
    "docs_minimal": {"mode": "docs", "url": "https://example.com/docs"},
    "docs_full": {"mode": "docs", "url": "https://example.com/docs", "limit": 5, "include_content": True, "content_limit": 1500}
}


def print_examples():
    """Print example usage patterns."""
    print("Example JSON inputs (for backward compatibility):")
    print()
    for name, item in EXAMPLE_INPUTS.items():
        print(f"# {name}")
        print(json.dumps(item, indent=2))
        print()
    
    print("Modern CLI usage examples:")
    print()
    print("# Search examples:")
    print("python3 main.py --search 'Next.js routing'")
    print("python3 main.py --search 'React hooks' --limit 5 --snippet-len 200")
    print()
    print("# Docs examples:")
    print("python3 main.py --docs 'https://ai-sdk.dev/docs/ai-sdk-ui/chatbot'")
    print("python3 main.py --docs 'https://nextjs.org/docs' --limit 3 --content-limit 2000")
    print()
    print("# Output to file:")
    print("python3 main.py --search 'Python FastAPI' --output results.json")
    print()


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Unifero CLI - Search web or crawl docs with enhanced extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --search "Next.js routing" --limit 3
  %(prog)s --docs "https://ai-sdk.dev/docs/ai-sdk-ui/chatbot"
  %(prog)s --search "Python FastAPI" --output results.json
  %(prog)s --examples  # Show all examples
  %(prog)s '{"mode":"search","query":"test"}'  # JSON mode (legacy)
        """
    )
    
    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--search", "-s",
        metavar="QUERY",
        help="Search mode: query to search for"
    )
    mode_group.add_argument(
        "--docs", "-d",
        metavar="URL", 
        help="Docs mode: base URL to crawl for documentation"
    )
    mode_group.add_argument(
        "--examples",
        action="store_true",
        help="Show example usage patterns and exit"
    )
    
    # Common options
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=5,
        help="Maximum number of results (default: 5, max 10 for docs)"
    )
    parser.add_argument(
        "--snippet-len",
        type=int,
        default=300,
        help="Maximum snippet length (default: 300)"
    )
    parser.add_argument(
        "--content-len", "--content-limit",
        type=int,
        default=2000,
        help="Maximum content length (default: 2000)"
    )
    
    # Docs-specific options
    parser.add_argument(
        "--no-content",
        action="store_true",
        help="Don't fetch page content (docs mode only)"
    )
    
    # Output options
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Write output to file instead of stdout"
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Compact JSON output"
    )
    
    # Legacy support
    parser.add_argument(
        "json_input",
        nargs="?",
        help="JSON input string (legacy mode)"
    )
    
    return parser


def validate_args(args: argparse.Namespace) -> Optional[str]:
    """Validate argument combinations and return error message if invalid."""
    if args.examples:
        return None
    
    if not args.search and not args.docs and not args.json_input:
        return "Must specify --search, --docs, or provide JSON input"
    
    if args.docs and args.limit > 10:
        return "Docs mode limit cannot exceed 10"
    
    if args.limit < 1:
        return "Limit must be at least 1"
    
    if args.snippet_len < 1:
        return "Snippet length must be at least 1"
    
    if args.content_len < 1:
        return "Content length must be at least 1"
        
    return None


def args_to_params(args: argparse.Namespace) -> Dict[str, Any]:
    """Convert parsed arguments to unifero tool parameters."""
    if args.search:
        return {
            "mode": "search",
            "query": args.search,
            "limit": args.limit,
            "snippet_len": args.snippet_len,
            "content_len": args.content_len
        }
    elif args.docs:
        return {
            "mode": "docs", 
            "url": args.docs,
            "limit": min(args.limit, 10),  # Enforce docs limit
            "include_content": not args.no_content,
            "content_limit": args.content_len
        }
    else:
        raise ValueError("No valid mode specified")


def format_output(data: Any, compact: bool = False) -> str:
    """Format output according to specified options."""
    if compact:
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    else:
        return json.dumps(data, indent=2, ensure_ascii=False)


def write_output(content: str, output_file: Optional[str]) -> None:
    """Write content to file or stdout with proper error handling."""
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Output written to {output_file}", file=sys.stderr)
        except PermissionError:
            print(f"❌ Permission denied writing to {output_file}", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"❌ Error writing to {output_file}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(content)


def legacy_json_mode(json_input: str) -> None:
    """Handle legacy JSON input mode with error handling."""
    try:
        params = json.loads(json_input)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(params, dict):
        print("❌ JSON input must be an object", file=sys.stderr)
        sys.exit(1)

    try:
        tool = UniferoTool()
        result = tool.process_request(params)
        print(format_output(result))
    except ValueError as e:
        print(f"❌ Invalid parameters: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error in legacy JSON mode")
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def _cli_main():
    """Main CLI entry point with enhanced error handling."""
    try:
        parser = create_parser()
        args = parser.parse_args()
        
        # Handle examples
        if args.examples:
            print_examples()
            return
        
        # Handle legacy JSON mode
        if args.json_input:
            legacy_json_mode(args.json_input)
            return
        
        # Handle environment variable fallback (legacy support)
        if not args.search and not args.docs:
            env_json = os.environ.get("UNIFERO_JSON")
            if env_json:
                legacy_json_mode(env_json)
                return
            
            # Check for piped input (legacy support)
            if not sys.stdin.isatty():
                try:
                    piped_input = sys.stdin.read().strip()
                    if piped_input:
                        legacy_json_mode(piped_input)
                        return
                except EOFError:
                    pass
                except Exception as e:
                    logger.debug(f"Error reading from stdin: {e}")
            
            # Show help if no input provided
            parser.print_help()
            return
        
        # Validate arguments
        error = validate_args(args)
        if error:
            print(f"❌ {error}", file=sys.stderr)
            parser.print_help()
            sys.exit(1)
        
        # Convert args to parameters
        try:
            params = args_to_params(args)
        except ValueError as e:
            print(f"❌ Invalid arguments: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Execute the request
        try:
            tool = UniferoTool()
            
            # Show progress for long operations
            if params.get("mode") == "docs":
                print(f"🔍 Crawling docs from {params['url']}...", file=sys.stderr)
            elif params.get("mode") == "search":
                print(f"🔍 Searching for '{params['query']}'...", file=sys.stderr)
            
            result = tool.process_request(params)
            
            # Format and output result
            formatted = format_output(result, args.compact)
            write_output(formatted, args.output)
            
        except ValueError as e:
            print(f"❌ Invalid parameters: {e}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled by user", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            logger.exception("Unexpected error during execution")
            print(f"❌ Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error in main")
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()


if __name__ == "__main__":
    _cli_main()


if __name__ == "__main__":
    _cli_main()
