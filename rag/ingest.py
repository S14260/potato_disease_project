import sys
import os

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(__file__))
)

from langchain_core.documents import Document
from rag.vectorstore import get_vectorstore, CHROMA_DIR
from knowledge.disease_db import disease_db
from knowledge.pesticide_db import pesticide_db
from knowledge.sop_db import sop_db


def build_disease_docs():
    docs = []
    for disease_id, info in disease_db.items():
        symptoms = info.get("symptom", {})
        spread = info.get("spread_conditions", [])
        pesticides = info.get("recommended_pesticides", [])
        strategies = info.get("treatment_strategy", {})

        strategy_text = ""
        for level, actions in strategies.items():
            strategy_text += f"\n  {level}: {'; '.join(actions)}"

        content = (
            f"病害名称: {info['name']}\n"
            f"类型: {info['type']}\n"
            f"病原: {info['pathogen']}\n"
            f"叶片症状: {symptoms.get('leaf', '')}\n"
            f"茎部症状: {symptoms.get('stem', '')}\n"
            f"块茎症状: {symptoms.get('tuber', '')}\n"
            f"传播条件: {', '.join(spread)}\n"
            f"推荐药剂: {', '.join(pesticides)}\n"
            f"防治策略:{strategy_text}"
        )
        docs.append(Document(
            page_content=content,
            metadata={"disease_id": disease_id, "type": "disease_info"},
        ))
    return docs


def build_pesticide_docs():
    docs = []
    for disease_id, pesticides in pesticide_db.items():
        for p in pesticides:
            content = (
                f"药剂名称: {p['name']}\n"
                f"有效成分: {p['ingredient']}\n"
                f"适用病害: {disease_id}\n"
                f"类型: {p['type']}\n"
                f"施药方式: {p['method']}\n"
                f"使用浓度: {p['dosage']}\n"
                f"施药间隔: {p['interval']}\n"
                f"适用阶段: {p['stage']}\n"
                f"风险提示: {p['risk']}\n"
                f"安全注意: {p['safety']}\n"
                f"补充说明: {p['note']}"
            )
            docs.append(Document(
                page_content=content,
                metadata={
                    "disease_id": disease_id,
                    "type": "pesticide",
                    "name": p["name"],
                },
            ))
    return docs


def build_sop_docs():
    docs = []
    for disease_id, risk_levels in sop_db.items():
        for risk_level, steps in risk_levels.items():
            steps_text = "\n".join(
                f"  步骤{s['step']}: {s['title']} - {s['content']}"
                for s in steps
            )
            content = (
                f"病害: {disease_id}\n"
                f"风险等级: {risk_level}\n"
                f"SOP流程:\n{steps_text}"
            )
            docs.append(Document(
                page_content=content,
                metadata={
                    "disease_id": disease_id,
                    "type": "sop",
                    "risk_level": risk_level,
                },
            ))
    return docs


def main():
    all_docs = []
    all_docs.extend(build_disease_docs())
    all_docs.extend(build_pesticide_docs())
    all_docs.extend(build_sop_docs())

    print(f"Total documents to ingest: {len(all_docs)}")

    vs = get_vectorstore()
    vs.add_documents(all_docs)

    print(f"Done. ChromaDB persisted at: {CHROMA_DIR}")


if __name__ == "__main__":
    main()
