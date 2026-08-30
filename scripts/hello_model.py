"""Küçük bir Foundry Local sohbet modeline tek soru gönderir."""

import argparse
from pathlib import Path
import sys
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5-0.5b", help="Katalogdaki model alias'ı.")
    parser.add_argument(
        "--prompt", default="Merhaba! Kendini Türkçe tek cümleyle tanıtır mısın?"
    )
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument(
        "--download", action="store_true", help="Model önbellekte yoksa indirmeye izin ver."
    )
    parser.add_argument("--model-cache-dir", type=Path, help="Mevcut model önbelleği klasörü.")
    args = parser.parse_args()
    if not args.prompt.strip():
        parser.error("Soru boş olamaz.")
    if args.max_tokens <= 0:
        parser.error("--max-tokens sıfırdan büyük olmalıdır.")

    try:
        from foundry_local_sdk import Configuration, FoundryLocalManager
    except ImportError as exc:
        print(f"SDK yüklenemedi; .venv Python ortamını kullanın. Ayrıntı: {exc}", file=sys.stderr)
        return 1

    app_data_dir = PROJECT_ROOT / "data" / "foundry"
    model_cache_dir = (
        args.model_cache_dir.expanduser().resolve()
        if args.model_cache_dir is not None
        else app_data_dir / "cache" / "models"
    )
    model = None
    loaded = False
    exit_code = 0
    try:
        print(f"Model önbelleği: {model_cache_dir}", flush=True)
        print("Foundry Local başlatılıyor; katalog sorgusu internet gerektirebilir.", flush=True)
        FoundryLocalManager.initialize(Configuration(
            app_name="offline_assistant",
            app_data_dir=str(app_data_dir),
            model_cache_dir=str(model_cache_dir),
        ))
        model = FoundryLocalManager.instance.catalog.get_model(args.model)
        if model is None:
            raise ValueError(f"Model bulunamadı: {args.model}. Önce list_models.py çalıştırın.")

        print(f"Seçili varyant: {model.id}", flush=True)
        if model.info.file_size_mb is not None:
            print(f"Katalogdaki model boyutu: {model.info.file_size_mb} MB", flush=True)
        if not model.is_cached:
            if not args.download:
                raise ValueError("Model indirilmemiş. İlk çalıştırmada --download ekleyin.")
            print("Model indiriliyor...", flush=True)
            last_percent = -10

            def report_progress(percent: float) -> None:
                nonlocal last_percent
                # İndirme çıktısını okunabilir tutmak için yaklaşık %10 aralıklarla yazdır.
                if int(percent) >= last_percent + 10 or (percent >= 100 and last_percent < 100):
                    last_percent = int(percent)
                    print(f"  İndirme: %{percent:.0f}", flush=True)

            model.download(report_progress)
        else:
            print("İndirilmiş model kullanılacak; yeniden indirilmiyor.", flush=True)

        print("Model belleğe yükleniyor...", flush=True)
        load_start = perf_counter()
        model.load()
        loaded = True
        print(f"Yükleme süresi: {perf_counter() - load_start:.2f} saniye", flush=True)
        client = model.get_chat_client()
        client.settings.max_tokens = args.max_tokens
        client.settings.temperature = 0.2
        messages = [
            {"role": "system", "content": "Türkçe, kısa ve anlaşılır cevap ver."},
            {"role": "user", "content": args.prompt.strip()},
        ]
        print(f"\nSoru: {args.prompt.strip()}\nCevap üretiliyor...", flush=True)
        answer_start = perf_counter()
        response = client.complete_chat(messages)
        elapsed = perf_counter() - answer_start
        if not response.choices or not (response.choices[0].message.content or "").strip():
            raise RuntimeError("Model boş cevap döndürdü.")
        print(f"\nCevap: {response.choices[0].message.content.strip()}", flush=True)
        print(f"\nCevap üretme süresi: {elapsed:.2f} saniye", flush=True)
        if response.choices[0].finish_reason == "length":
            print("Uyarı: Cevap token sınırına ulaştı; --max-tokens artırılabilir.")
        print("Bu bir model denemesidir; henüz belgelerden arama (RAG) yapılmaz.")
    except KeyboardInterrupt:
        print("\nİşlem kullanıcı tarafından durduruldu.", file=sys.stderr)
        exit_code = 130
    except Exception as exc:
        print(f"Yerel model denemesi başarısız: {exc}", file=sys.stderr)
        exit_code = 1
    finally:
        if loaded:
            try:
                model.unload()
                print("Model bellekten çıkarıldı; indirilen dosyalar önbellekte kaldı.")
            except Exception as exc:
                print(f"Model bellekten çıkarılamadı: {exc}", file=sys.stderr)
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
