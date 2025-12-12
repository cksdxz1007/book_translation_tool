import re
import logging

logger = logging.getLogger(__name__)

def _split_text_by_sentences(text, max_char_limit):
    """
    Splits a text into sentences and then groups them into chunks under max_char_limit.
    If a single sentence exceeds the limit, it's split hard at the limit.
    """
    if not text:
        return []

    # More comprehensive sentence terminators, including CJK
    sentence_enders = re.compile(r'(?<=[.!?。！？])\s+|(?<=\n)')
    sentences = sentence_enders.split(text)
    sentences = [s.strip() for s in sentences if s and s.strip()]

    if not sentences:
        # If no sentences were found (e.g. a very long string with no terminators),
        # fall back to hard splitting.
        if len(text) > max_char_limit:
            logger.warning(f"A long text block (length {len(text)}) without clear sentence breaks had to be hard split at {max_char_limit} characters.")
            return [text[i:i + max_char_limit] for i in range(0, len(text), max_char_limit)]
        return [text] if text else []

    current_chunk_parts = []
    current_chunk_len = 0
    final_chunks = []

    for sentence in sentences:
        sentence_len = len(sentence)
        if sentence_len > max_char_limit:
            # Split the oversized sentence itself
            if current_chunk_parts: # Add previous parts as a chunk
                final_chunks.append(" ".join(current_chunk_parts))
                current_chunk_parts = []
                current_chunk_len = 0
            
            logger.warning(f"A single sentence (length {sentence_len}) exceeded max_char_limit ({max_char_limit}) and was hard split.")
            for i in range(0, sentence_len, max_char_limit):
                final_chunks.append(sentence[i:i + max_char_limit])
        elif current_chunk_len + sentence_len + (1 if current_chunk_parts else 0) <= max_char_limit:
            current_chunk_parts.append(sentence)
            current_chunk_len += sentence_len + (1 if len(current_chunk_parts) > 1 else 0)
        else:
            if current_chunk_parts:
                final_chunks.append(" ".join(current_chunk_parts))
            current_chunk_parts = [sentence]
            current_chunk_len = sentence_len
    
    if current_chunk_parts:
        final_chunks.append(" ".join(current_chunk_parts))
        
    return final_chunks


def split_markdown_into_chunks(markdown_text, max_chunk_size=1500):
    """
    Splits Markdown text into manageable chunks for translation,
    respecting Markdown block structures (paragraphs, headers, lists, code blocks, page comments)
    and then sentences.

    Args:
        markdown_text (str): The Markdown text to split.
        max_chunk_size (int): The maximum character size for each chunk.

    Returns:
        list[str]: A list of Markdown text chunks.
    """
    if not markdown_text or not markdown_text.strip():
        return []

    chunks = []
    # Split by two or more newlines, which typically separate Markdown blocks
    # Also capture the separators to potentially re-add them if needed, or just use them as split points
    atomic_blocks = re.split(r'(\n\n+)', markdown_text)
    
    processed_blocks = []
    # Combine text parts with their subsequent multi-newline separators
    i = 0
    while i < len(atomic_blocks):
        block_content = atomic_blocks[i]
        if i + 1 < len(atomic_blocks):
            # separator = atomic_blocks[i+1] # We don't strictly need the separator itself for this logic
            processed_blocks.append(block_content)
        else:
            processed_blocks.append(block_content)
        i += 2 # Move past content and separator if it existed
    
    # Filter out any empty strings that might result from split and strip whitespace
    processed_blocks = [block.strip() for block in processed_blocks if block and block.strip()]

    current_chunk_elements = []
    current_length = 0

    for block in processed_blocks:
        block_len = len(block)
        # Page comments are usually small and should be kept as their own chunk or with minimal text
        is_page_comment = block.startswith("<!-- Page ") and block.endswith(" -->")

        if is_page_comment:
            # If there's an existing chunk, finalize it
            if current_chunk_elements:
                chunks.append("\n\n".join(current_chunk_elements))
                current_chunk_elements = []
                current_length = 0
            chunks.append(block) # Add page comment as its own chunk
            continue

        if block_len > max_chunk_size:
            # If current_chunk_elements has content, finalize it first
            if current_chunk_elements:
                chunks.append("\n\n".join(current_chunk_elements))
                current_chunk_elements = []
                current_length = 0
            
            # Split the oversized block by sentences
            sub_chunks = _split_text_by_sentences(block, max_chunk_size)
            chunks.extend(sub_chunks) # Add all resulting sub-chunks
        
        # Try to add the current block to the current_chunk_elements
        # The +2 is for the "\n\n" separator when joining if current_chunk_elements is not empty
        elif current_length + block_len + (2 if current_chunk_elements else 0) <= max_chunk_size:
            current_chunk_elements.append(block)
            current_length += block_len + (2 if len(current_chunk_elements) > 1 else 0) # only add 2 if more than one element already
        else:
            # Finalize the current chunk and start a new one with the current block
            if current_chunk_elements:
                chunks.append("\n\n".join(current_chunk_elements))
            current_chunk_elements = [block]
            current_length = block_len

    # Add any remaining chunk
    if current_chunk_elements:
        chunks.append("\n\n".join(current_chunk_elements))

    return [chunk for chunk in chunks if chunk.strip()] # Ensure no empty chunks are returned

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    sample_md = """<!-- Page 1 -->

# This is a Header

This is the first paragraph. It has some sentences. Let\'s make it a bit longer to see how it behaves.
This is still the first paragraph and it\'s getting quite long.

This is a second paragraph. Shorter.

<!-- Page 2 -->

This paragraph is intentionally very_long_to_test_the_splitting_mechanism_when_a_single_block_exceeds_the_max_chunk_size_it_should_be_broken_down_further_hopefully_by_sentences_first_and_then_if_a_sentence_is_too_long_it_will_be_hard_split_at_the_character_limit_producing_a_warning_message_in_the_logs_for_us_to_see_and_potentially_address_if_it_happens_too_often_or_causes_issues_with_translation_quality_or_context_retention_across_the_split_points_which_is_always_a_concern. This is a test sentence. And another one.

- List item 1
- List item 2
  - Sublist item 2.1

Another paragraph after the list.
"""

    short_md = """<!-- Page 1 -->\n\nJust one line."""
    
    very_long_sentence_md = """<!-- Page 1 -->\n\nThisIsAVeryLongSingleSentenceWithoutAnySpacesOrPunctuationMarksThatExceedsTheTypicalCharacterLimitForTranslationChunksItWillTestTheHardSplittingLogicWithinTheSentenceSplitterFunctionAndShouldIdeallyProduceAWarningInTheLogsIndicatingThatASentenceWasForcefullyBrokenApartBecauseItWasTooLarge."""


    print("--- Testing with sample_md ---")
    chunks = split_markdown_into_chunks(sample_md, max_chunk_size=150)
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1} (len: {len(chunk)}):\n---\n{chunk}\n---\n")

    print("\n--- Testing with short_md ---")
    chunks_short = split_markdown_into_chunks(short_md, max_chunk_size=150)
    for i, chunk in enumerate(chunks_short):
        print(f"Chunk {i+1} (len: {len(chunk)}):\n---\n{chunk}\n---\n")

    print("\n--- Testing with very_long_sentence_md ---")
    # Expect a warning for the very long sentence
    chunks_long_sentence = split_markdown_into_chunks(very_long_sentence_md, max_chunk_size=80)
    for i, chunk in enumerate(chunks_long_sentence):
        print(f"Chunk {i+1} (len: {len(chunk)}):\n---\n{chunk}\n---\n")

    empty_md = ""
    print("\n--- Testing with empty_md ---")
    chunks_empty = split_markdown_into_chunks(empty_md, max_chunk_size=150)
    print(f"Number of chunks for empty_md: {len(chunks_empty)}")
    if not chunks_empty:
        print("Correctly produced no chunks.")

    whitespace_md = "   \n\n   "
    print("\n--- Testing with whitespace_md ---")
    chunks_whitespace = split_markdown_into_chunks(whitespace_md, max_chunk_size=150)
    print(f"Number of chunks for whitespace_md: {len(chunks_whitespace)}")
    if not chunks_whitespace:
        print("Correctly produced no chunks.")
        
    # Test case for a block that is large but splittable by sentences
    md_splittable_block = """This is the first sentence of a large block. This is the second sentence, which helps to make the block larger than the typical chunk size but still manageable. This is the third sentence, further extending it. If all these sentences together are too long, they should be split into multiple chunks, but each chunk should respect sentence boundaries if possible. This is the final sentence of this specific block.
    
Another paragraph."""
    print("\n--- Testing with md_splittable_block (max_chunk_size=100) ---")
    chunks_splittable = split_markdown_into_chunks(md_splittable_block, max_chunk_size=100)
    for i, chunk in enumerate(chunks_splittable):
        print(f"Chunk {i+1} (len: {len(chunk)}):\n---\n{chunk}\n---\n") 