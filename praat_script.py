from pathlib import Path

from encoding import discover_scripts


def update(logger, path: Path, script_id: str, content: str, create_backup: bool = True) -> dict:
    """
    기존 Praat 스크립트 내용 업데이트.
    - script_id: 스크립트 ID (예: 'jitter-shimmer')
    - content: 새로운 스크립트 내용
    - create_backup: 백업 파일 생성 여부 (.praat.bak)
    """
    scripts = discover_scripts(path)
    if script_id not in scripts:
        raise ValueError(f"Unknown script_id: {script_id}")
    
    script_path = scripts[script_id]
    
    # 백업 생성
    backup_path = None
    if create_backup:
        backup_path = script_path.with_suffix('.praat.bak')
        try:
            import shutil
            shutil.copy2(script_path, backup_path)
            logger.info("Backup created: %s", backup_path)
        except Exception as e:
            logger.warning("Backup failed: %s", e)
            backup_path = None
    
    # UTF-8로 저장 (Praat 표준)
    try:
        script_path.write_text(content, encoding='utf-8')
        logger.info("Script updated: %s", script_path)
    except Exception as e:
        logger.error("Failed to update script: %s", e)
        raise
    
    return {
        "script_id": script_id,
        "path": str(script_path),
        "backup": str(backup_path) if backup_path else None,
        "status": "updated",
        "size": len(content),
    }

def create(logger, path: Path, filename: str, content: str, overwrite: bool = False) -> dict:
    """
    새 Praat 스크립트 생성.
    - filename: 파일명 (자동으로 .praat 확장자 추가)
    - content: 스크립트 내용
    - overwrite: 기존 파일 덮어쓰기 허용 여부
    """
    # .praat 확장자 자동 추가
    if not filename.endswith('.praat'):
        filename += '.praat'
    
    script_path = (path / filename).resolve()
    
    # 경로 검증 (script_dir 밖으로 나가지 않도록)
    if not str(script_path).startswith(str(path)):
        raise ValueError(f"Invalid path: {script_path}")
    
    # 기존 파일 확인
    if script_path.exists() and not overwrite:
        raise ValueError(f"Script already exists: {filename}. Use overwrite=True to replace.")
    
    # UTF-8로 저장
    try:
        script_path.write_text(content, encoding='utf-8')
        logger.info("Script created: %s", script_path)
    except Exception as e:
        logger.error("Failed to create script: %s", e)
        raise
    
    script_id = script_path.stem
    
    return {
        "script_id": script_id,
        "filename": filename,
        "path": str(script_path),
        "status": "created",
        "size": len(content),
    }


def delete(logger, path: Path, script_id: str, create_backup: bool = True) -> dict:
    """
    Praat 스크립트 삭제.
    - script_id: 스크립트 ID
    - create_backup: 삭제 전 백업 생성 여부 (.praat.deleted)
    """
    scripts = discover_scripts(path)
    if script_id not in scripts:
        raise ValueError(f"Unknown script_id: {script_id}")
    
    script_path = scripts[script_id]
    
    # 백업 생성
    backup_path = None
    if create_backup:
        backup_path = script_path.with_suffix('.praat.deleted')
        try:
            import shutil
            shutil.copy2(script_path, backup_path)
            logger.info("Backup before deletion: %s", backup_path)
        except Exception as e:
            logger.warning("Backup failed: %s", e)
            backup_path = None
    
    # 삭제
    try:
        script_path.unlink()
        logger.info("Script deleted: %s", script_path)
    except Exception as e:
        logger.error("Failed to delete script: %s", e)
        raise
    
    return {
        "script_id": script_id,
        "path": str(script_path),
        "backup": str(backup_path) if backup_path else None,
        "status": "deleted",
    }
