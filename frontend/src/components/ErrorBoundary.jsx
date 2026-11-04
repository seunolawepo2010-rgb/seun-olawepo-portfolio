import { Component } from "react";

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidUpdate(prev) {
    if (prev.resetKey !== this.props.resetKey && this.state.failed) this.setState({ failed: false });
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="mx-auto max-w-xl px-5 py-16 text-center" data-testid="page-error">
        <h2 className="font-heading text-xl font-bold">This section could not be displayed</h2>
        <p className="mt-2 text-sm text-slate-600">Please reload the page. The rest of the portfolio is still available from the menu.</p>
        <button onClick={() => window.location.reload()} className="mt-4 rounded-md bg-teal-700 px-4 py-2 text-sm text-white hover:bg-teal-800" data-testid="page-error-reload">Reload page</button>
      </div>
    );
  }
}
