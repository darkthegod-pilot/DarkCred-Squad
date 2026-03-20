#!/usr/bin/env python3
import argparse
import sys

from dotenv import load_dotenv

from darkcred.config import SEGMENTS
from darkcred.generator import GenerationError, generate_variations
from darkcred.output import save_output
from darkcred.validator import validate_all


def parse_args() -> argparse.Namespace:
    segment_choices = list(SEGMENTS.keys()) + ["all"]

    parser = argparse.ArgumentParser(
        prog="darkcred-generator",
        description="Gerador de copy para anúncios Instagram — DarkCred",
    )
    parser.add_argument(
        "--segment",
        choices=segment_choices,
        default="generic",
        help="Segmento alvo. Use 'all' para todos os segmentos. (padrão: generic)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Número de variações por segmento. (padrão: 5)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Diretório para salvar os arquivos gerados. (padrão: ./output)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text", "both"],
        default="both",
        help="Formato de saída. (padrão: both)",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-6",
        help="Modelo Claude a usar. (padrão: claude-sonnet-4-6)",
    )
    parser.add_argument(
        "--list-segments",
        action="store_true",
        help="Lista os segmentos disponíveis e sai.",
    )
    return parser.parse_args()


def list_segments() -> None:
    print("Segmentos disponíveis:\n")
    for key, seg in SEGMENTS.items():
        print(f"  {key:<12} {seg['label']}")
    print("\nUse --segment all para rodar todos.")


def run_segment(
    segment_key: str, count: int, model: str, output_dir: str, fmt: str
) -> tuple[int, int]:
    label = SEGMENTS[segment_key]["label"]
    print(f"\nGerando {count} variações para: {label}...")

    try:
        variations = generate_variations(segment_key, count, model)
    except GenerationError as e:
        print(f"  ERRO: {e}", file=sys.stderr)
        return 0, 0

    compliant, violations = validate_all(variations)

    if violations:
        print(f"  {len(violations)} variação(ões) reprovada(s) na validação de compliance:")
        for v in violations:
            print(f"    - {v}")

    print(f"  {len(compliant)} variação(ões) aprovada(s)")

    if compliant:
        saved = save_output(compliant, segment_key, output_dir, fmt)
        for file_type, path in saved.items():
            print(f"  Salvo ({file_type}): {path}")

        print("\n  Preview das variações aprovadas:")
        for i, var in enumerate(compliant, 1):
            print(f"\n  [{i}]")
            for line in var.get("full_copy", "").splitlines():
                print(f"      {line}")

    return len(compliant), len(violations)


def main() -> None:
    load_dotenv()
    args = parse_args()

    if args.list_segments:
        list_segments()
        return

    segments = list(SEGMENTS.keys()) if args.segment == "all" else [args.segment]

    total_compliant = 0
    total_violations = 0

    for seg_key in segments:
        compliant, violations = run_segment(
            seg_key, args.count, args.model, args.output_dir, args.format
        )
        total_compliant += compliant
        total_violations += violations

    if len(segments) > 1:
        print(f"\n{'=' * 50}")
        print(f"Total: {total_compliant} aprovadas, {total_violations} reprovadas")


if __name__ == "__main__":
    main()
