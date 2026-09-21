#!/usr/bin/env python3
"""Repair P2-P5 assigned source metadata. Every value derived from evidence and
double-checked; refuses to write if anything fails.

math     : locate the pinned record by PROBLEM TEXT (unique), confirm its final
           answer equals the source's gold, then set answer_source and correct
           source_record_locator, which was fabricated from the task id.
planning : locate the PlanBench instance by domain + instance id, confirm its
           ground_truth_plan equals the source's gold, then set answer_source.
recipe   : M4 -- the value on all 103 other records in the batch.
license  : the note this same file already uses for the same pinned snapshot.
"""
import json, sys, collections, re

MATH_PATH="sources/upstream_interrupt_lrm/math_source_problems.jsonl"
PB_PATH="sources/planbench/task1_blocksworld_logistics.jsonl"
snap=[json.loads(l) for l in open(MATH_PATH) if l.strip()]
pb=[json.loads(l) for l in open(PB_PATH) if l.strip()]
def final(r):
    a=str(r.get("original_answer","")).strip()
    return a.split("####")[-1].strip() if "####" in a else a
def norm(s): return " ".join(str(s).split())
by_problem={}
for i,r in enumerate(snap,1): by_problem.setdefault(norm(r.get("original_problem")),[]).append((i,r))
pb_by={(r["upstream_domain"],str(r["upstream_instance_id"])):r for r in pb}

def fix(r, problems):
    tid,fam=r["task_group_id"],r["source_family"]; new=dict(r)
    if fam.startswith("plan"):
        import hashlib
        dom="blocksworld" if fam=="plan_blocks" else "logistics"
        base,_,rest=r["source_record_locator"].partition("#")
        frag,_,inst=rest.partition(":")
        if base!=PB_PATH or frag!=dom:
            problems.append(f"{tid}: locator disagrees with family {fam}"); return None
        rec=pb_by.get((dom,inst))
        if rec is None:
            problems.append(f"{tid}: no PlanBench instance {dom}/{inst}"); return None
        up=rec["ground_truth_plan"]; gold=r["original_answer"]; df=r.get("derived_from")
        if r.get("source_admission_status")=="derived_from_pinned":
            if not isinstance(df,dict):
                problems.append(f"{tid}: derived_from_pinned without derived_from"); return None
            if hashlib.sha256(up.encode()).hexdigest()!=df.get("upstream_gold_sha256"):
                problems.append(f"{tid}: upstream_gold_sha256 mismatch"); return None
            ua=[x for x in up.splitlines() if x.strip()]; ga=[x for x in gold.splitlines() if x.strip()]
            n=df.get("gold_prefix_actions")
            if len(ga)!=n or [norm(x) for x in ua[:n]]!=[norm(x) for x in ga]:
                problems.append(f"{tid}: gold is not the declared {n}-action prefix"); return None
        elif norm(up)!=norm(gold):
            problems.append(f"{tid}: PlanBench plan != source gold"); return None
        new["answer_source"]={"field":"ground_truth_plan","kind":"pinned_upstream_record","line":None,"path":PB_PATH}
        return new
    cands=by_problem.get(norm(r["statement"]),[])
    if len(cands)!=1:
        problems.append(f"{tid}: {len(cands)} problem-text matches in the snapshot"); return None
    n,rec=cands[0]
    if final(rec)!=str(r["original_answer"]).strip():
        problems.append(f"{tid}: line {n} answer {final(rec)!r} != gold {r['original_answer']!r}"); return None
    new["answer_source"]={"field":"original_answer",
        "final_answer_marker":"####" if "####" in str(rec.get("original_answer","")) else None,
        "kind":"pinned_upstream_record","line":n,"path":MATH_PATH}
    new["source_record_locator"]=f"{MATH_PATH}:{n}"
    return new

def main(write, people, correct_existing):
    tot=collections.Counter(); probs=[]; staged={}; relocated=[]; corrected=[]
    for p in people:
        path=f"data/smoke_20_v38/contributors/{p}/assigned_source_groups.jsonl"
        recs=[json.loads(l) for l in open(path) if l.strip()]
        notes={r["license_note"] for r in recs if r["source_family"]=="gsm8k" and "license_note" in r}
        if len(notes)!=1:
            probs.append(f"{p}: ambiguous snapshot license_note {notes}"); continue
        note=notes.pop(); out=[]
        for r in recs:
            n=fix(r,probs)
            if n is None: out.append(r); continue
            if "answer_source" not in r: tot["answer_source"]+=1
            elif n["answer_source"]!=r["answer_source"]:
                if correct_existing:
                    tot["answer_source corrected"]+=1
                    corrected.append((r["task_group_id"], r["answer_source"], n["answer_source"]))
                else:
                    n["answer_source"]=r["answer_source"]
            if n.get("source_record_locator")!=r.get("source_record_locator"):
                tot["source_record_locator corrected"]+=1
                relocated.append(f"{r['task_group_id']}: {r['source_record_locator'].rpartition(':')[2]} -> {n['source_record_locator'].rpartition(':')[2]}")
            if "recipe" not in n: n["recipe"]="M4"; tot["recipe"]+=1
            if "license_note" not in n: n["license_note"]=note; tot["license_note"]+=1
            out.append(n)
        staged[path]=out
    if probs:
        print("REFUSING TO WRITE:"); [print("  -",x) for x in probs]; return 1
    print("every record verified twice (located by text/id, confirmed by gold answer)")
    print("changes:", dict(tot))
    print("\nlocator corrections (first 8):")
    for x in relocated[:8]: print("   ",x)
    if corrected:
        print(f"\nanswer_source corrections ({len(corrected)}):")
        for tid,old,new in corrected:
            print(f"    {tid:22} line {old.get('line')} -> {new.get('line')}   marker {old.get('final_answer_marker')!r} -> {new.get('final_answer_marker')!r}")
    if write:
        for path,out in staged.items():
            with open(path,"w",encoding="utf-8") as fh:
                for r in out: fh.write(json.dumps(r,ensure_ascii=False)+"\n")
            print(f"  wrote {path} ({len(out)})")
    else: print("\n(dry run)")
    return 0
_people=[a for a in sys.argv[1:] if a.startswith("P") and a[1:].isdigit()] or ["P2","P3","P4","P5"]
sys.exit(main("--write" in sys.argv, _people, "--correct-existing" in sys.argv))
