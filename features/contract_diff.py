from pipelines.diff_engine import ContractDiffEngine


def run_contract_diff(pdf1_path, pdf2_path):
    try:
        engine = ContractDiffEngine()
        stats, path_removed, path_added = engine.compare(pdf1_path, pdf2_path)

        results = {
            "pages1": stats["pages1"],
            "pages2": stats["pages2"],
            "path_removed": path_removed,
            "path_added": path_added
        }
        return results, None
    except Exception as e:
        return {}, str(e)