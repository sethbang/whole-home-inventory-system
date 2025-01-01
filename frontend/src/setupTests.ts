import '@testing-library/jest-dom';

// Mock TextEncoder/TextDecoder
class MockTextEncoder {
  encode(input: string): Uint8Array {
    return new Uint8Array(Buffer.from(input));
  }
}

class MockTextDecoder {
  decode(input?: Uint8Array): string {
    if (!input) return '';
    return Buffer.from(input).toString();
  }
}

Object.defineProperty(global, 'TextEncoder', {
  value: MockTextEncoder,
});

Object.defineProperty(global, 'TextDecoder', {
  value: MockTextDecoder,
});