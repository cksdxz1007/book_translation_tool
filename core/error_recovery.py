"""
Error recovery strategies for translation operations.

This module provides automatic error recovery for translation operations,
including content splitting at natural boundaries and retry mechanisms.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable, Tuple


@dataclass
class RecoveryResult:
    """Result of an error recovery attempt.

    Attributes:
        success: Whether the recovery was successful.
        data: The recovered data (translated content if successful).
        fallback_used: Whether a fallback strategy was used.
        message: Human-readable message describing the result.
    """
    success: bool
    data: Any = None
    fallback_used: bool = False
    message: str = ""


class ContentSplitter:
    """Handles splitting content when it's too large for a single request.

    This class provides methods to split content at natural boundaries
    (punctuation, newlines, spaces) to facilitate retry on partial failures.
    """

    BOUNDARY_CHARS = ('.', '!', '?', '\n', ' ')

    @staticmethod
    def split_at_boundary(
        content: str,
        target_ratio: float = 0.5
    ) -> Tuple[str, str]:
        """Split content at a natural boundary near the target ratio position.

        Searches for the nearest natural boundary (., !, ?, \n, space) to the
        target position defined by target_ratio * len(content).

        Args:
            content: The content to split.
            target_ratio: The ratio (0.0-1.0) indicating where to aim for split.
                         Default 0.5 means split near the middle.

        Returns:
            A tuple of (first_part, second_part) after splitting at a natural
            boundary as close to target_ratio as possible.
        """
        if not content or len(content) < 100:
            mid = len(content) // 2
            return content[:mid], content[mid:]

        target_pos = int(len(content) * target_ratio)
        search_window = len(content) // 10

        best_split_pos = target_pos
        for boundary in ContentSplitter.BOUNDARY_CHARS:
            search_start = max(0, target_pos - search_window)
            search_end = min(len(content), target_pos + search_window)
            search_area = content[search_start:search_end]
            boundary_pos = search_area.rfind(boundary)
            if boundary_pos != -1:
                actual_pos = search_start + boundary_pos + len(boundary)
                if abs(actual_pos - target_pos) < abs(best_split_pos - target_pos):
                    best_split_pos = actual_pos
                    break

        return content[:best_split_pos].strip(), content[best_split_pos:].strip()

    @staticmethod
    def split_into_n_parts(content: str, n: int) -> List[str]:
        """Split content into n roughly equal parts.

        Uses split_at_boundary recursively to divide content into n parts
        of roughly equal length.

        Args:
            content: The content to split.
            n: The number of parts to split into (must be >= 2).

        Returns:
            A list of n content parts, each stripped of leading/trailing whitespace.
        """
        if n < 2:
            return [content]

        if n == 2:
            return list(ContentSplitter.split_at_boundary(content, 0.5))

        # Recursively split: first split in half, then split the second part
        parts = []
        mid_ratio = 1.0 / n
        first_part, remainder = ContentSplitter.split_at_boundary(content, mid_ratio)
        parts.append(first_part)

        # Recursively split remainder into (n-1) parts
        remaining_parts = ContentSplitter.split_into_n_parts(remainder, n - 1)
        parts.extend(remaining_parts)

        return parts


class ErrorRecoveryManager:
    """Manages error recovery strategies for translation operations.

    This class provides async methods for recovering from various translation
    failures including chunk failures and context overflow errors.

    Attributes:
        log_callback: Optional callback for logging (log_type, message).
        recovery_stats: Dictionary tracking recovery attempts by type.
    """

    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None):
        """Initialize the ErrorRecoveryManager.

        Args:
            log_callback: Optional callback function that takes (log_type, message)
                         for logging purposes.
        """
        self.log_callback = log_callback
        self._recovery_stats: Dict[str, int] = {}

    def _log(self, log_type: str, message: str):
        """Log a message if a log callback is configured.

        Args:
            log_type: The type of log (e.g., 'info', 'warning', 'error').
            message: The message to log.
        """
        if self.log_callback:
            self.log_callback(log_type, message)

    def _record_recovery(self, recovery_type: str):
        """Record a recovery attempt for statistics tracking.

        Args:
            recovery_type: The type of recovery (e.g., 'chunk_failure').
        """
        self._recovery_stats[recovery_type] = self._recovery_stats.get(recovery_type, 0) + 1

    def get_recovery_stats(self) -> Dict[str, int]:
        """Get a copy of the recovery statistics.

        Returns:
            A dictionary mapping recovery types to their attempt counts.
        """
        return self._recovery_stats.copy()

    async def recover_from_chunk_failure(
        self,
        content: str,
        translate_func: Callable[[str], Any],
        max_splits: int = 3
    ) -> RecoveryResult:
        """Recover from chunk failure by splitting at natural boundaries.

        When a translation chunk fails (e.g., due to content size or timeout),
        this method attempts to recover by progressively splitting the content
        into more parts and translating them individually.

        Args:
            content: The content that failed to translate.
            translate_func: An async function that takes content and returns
                            translated content.
            max_splits: Maximum number of split attempts (default 3).
                       The content will be split into up to max_splits parts.

        Returns:
            A RecoveryResult indicating success or failure. On success,
            data contains the combined translated content.
        """
        self._log("info", "Attempting recovery from chunk failure")
        self._record_recovery("chunk_failure")

        n_parts = 2
        for attempt in range(max_splits):
            try:
                self._log("info", f"Splitting content into {n_parts} parts (attempt {attempt + 1}/{max_splits})")
                parts = ContentSplitter.split_into_n_parts(content, n_parts)
                translated_parts = []
                for i, part in enumerate(parts):
                    self._log("info", f"Translating part {i + 1}/{len(parts)}")
                    translated_part = await translate_func(part)
                    translated_parts.append(translated_part)
                combined = " ".join(translated_parts)
                self._log("info", f"Successfully recovered by splitting into {n_parts} parts")
                return RecoveryResult(
                    success=True,
                    data=combined,
                    fallback_used=True,
                    message=f"Split into {n_parts} parts"
                )
            except Exception as e:
                self._log("warning", f"Recovery attempt {attempt + 1} failed: {e}")
                n_parts += 1
                continue

        return RecoveryResult(
            success=False,
            message=f"Could not recover after {max_splits} split attempts"
        )

    async def recover_partial_results(
        self,
        failed_units: List[Dict[str, Any]],
        translate_func: Callable[[Dict[str, Any]], Any],
        max_concurrent: int = 3
    ) -> RecoveryResult:
        """Attempt to recover failed translation units.

        Attempts to translate failed units individually, potentially using
        a lower concurrency level to avoid rate limits or overload.

        Args:
            failed_units: List of failed translation unit dictionaries.
                         Each unit should contain content and metadata needed
                         for translation.
            translate_func: An async function that takes a unit dict and returns
                          a translated unit dict.
            max_concurrent: Maximum concurrent translation requests (default 3).

        Returns:
            A RecoveryResult indicating success or failure. On success,
            data contains the list of successfully translated units.
        """
        self._log("info", f"Attempting to recover {len(failed_units)} failed units")
        self._record_recovery("partial_results")

        if not failed_units:
            return RecoveryResult(
                success=True,
                data=[],
                message="No failed units to recover"
            )

        translated_units = []
        errors = []

        # Process units with limited concurrency
        for i in range(0, len(failed_units), max_concurrent):
            batch = failed_units[i:i + max_concurrent]
            batch_results = []

            for unit in batch:
                try:
                    self._log("info", f"Translating failed unit")
                    result = await translate_func(unit)
                    batch_results.append(result)
                except Exception as e:
                    self._log("warning", f"Failed to recover unit: {e}")
                    errors.append(str(e))

            translated_units.extend(batch_results)

        if translated_units:
            self._log("info", f"Successfully recovered {len(translated_units)}/{len(failed_units)} units")
            return RecoveryResult(
                success=True,
                data=translated_units,
                fallback_used=True,
                message=f"Recovered {len(translated_units)}/{len(failed_units)} units"
            )
        else:
            self._log("error", f"Failed to recover any units: {'; '.join(errors)}")
            return RecoveryResult(
                success=False,
                message=f"Could not recover any units: {'; '.join(errors)}"
            )
