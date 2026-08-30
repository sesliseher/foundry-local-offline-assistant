"""Foundry Local kataloğunu ve indirilen modelleri listeler; model indirmez."""

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-cache-dir",
        type=Path,
        help="Önceden indirilmiş modeller varsa onların önbellek klasörü.",
    )
    args = parser.parse_args()

    try:
        from foundry_local_sdk import Configuration, FoundryLocalManager
    except ImportError as exc:
        print(
            "SDK yüklenemedi. Betiği projenin .venv Python ortamıyla çalıştırın."
            f"\nAyrıntı: {exc}",
            file=sys.stderr,
        )
        return 1

    # SDK katalog ve günlük dosyalarını proje içinde tutarız.
    app_data_dir = PROJECT_ROOT / "data" / "foundry"
    model_cache_dir = (
        args.model_cache_dir.expanduser().resolve()
        if args.model_cache_dir is not None
        else app_data_dir / "cache" / "models"
    )
    print(f"Model önbelleği: {model_cache_dir}", flush=True)
    print(
        "Katalog okunuyor (ilk kullanımda internet gerekebilir). "
        "Model indirme veya yükleme yapılmayacak.",
        flush=True,
    )

    try:
        config = Configuration(
            app_name="offline_assistant",
            app_data_dir=str(app_data_dir),
            model_cache_dir=str(model_cache_dir),
        )
        FoundryLocalManager.initialize(config)
        catalog = FoundryLocalManager.instance.catalog
        models = sorted(catalog.list_models(), key=lambda model: model.alias)
        cached_models = sorted(catalog.get_cached_models(), key=lambda model: model.id)
    except Exception as exc:
        print(
            f"Foundry Local kataloğu okunamadı: {exc}\n"
            "İnternet bağlantısını, önbellek klasörü izinlerini ve SDK/runtime "
            "kurulumunu kontrol edin. Listeleme başarısız olduğu için model "
            "önbelleğinin boş olduğu sonucuna varılamaz.",
            file=sys.stderr,
        )
        return 1

    # Önbellek model varyantı bazındadır: aynı alias'ın CPU/GPU sürümleri farklıdır.
    cached_ids = {model.id for model in cached_models}
    print(f"\nKatalog: {len(models)} model alias'ı")
    if not models:
        print("Katalogda model bulunamadı.")
    for model in models:
        status = "İndirilmiş" if model.id in cached_ids else "İndirilmemiş"
        print(f"\n  {model.alias} | {model.capabilities or 'Yetenek bilgisi yok'}")
        print(f"    Seçili varyant: {model.id}")
        print(f"    Önbellek: {status}")

    print(f"\nBu önbellekte indirilen varyant sayısı: {len(cached_models)}")
    for model in cached_models:
        print(f"  {model.alias}: {model.id}")
    if not cached_models:
        print(
            "Bu klasörde indirilmiş model bulunamadı. Başka bir uygulamanın "
            "indirdiği modeller farklı bir önbellekte olabilir; o klasörü "
            "--model-cache-dir ile belirtebilirsiniz."
        )
    print("\nKatalogda görünmek, modelin indirildiği veya çalıştırıldığı anlamına gelmez.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
