"""Runner incremental unificado para TSP e roteamento hospitalar."""
import logging, secrets, statistics, time, traceback
from dataclasses import replace
from optimizers import GeneticOptimizer, NearestNeighborOptimizer, HospitalGeneticOptimizer, HospitalGreedyOptimizer
from .models import *
from .statistics import consolidate, improvement_percentage

log=logging.getLogger(__name__)
def create_optimizer(problem_type, algorithm_mode):
    table={(ProblemType.TSP,AlgorithmMode.GENETIC):GeneticOptimizer,(ProblemType.TSP,AlgorithmMode.HEURISTIC):NearestNeighborOptimizer,
           (ProblemType.HOSPITAL,AlgorithmMode.GENETIC):HospitalGeneticOptimizer,(ProblemType.HOSPITAL,AlgorithmMode.HEURISTIC):HospitalGreedyOptimizer}
    return table[(problem_type,algorithm_mode)]()

class ExperimentRunner:
    def __init__(self, cities=None): self._legacy_cities=tuple(cities or ()); self.clear()
    def clear(self):
        self.state=ProcessingState.IDLE; self.request=None; self.config=None; self.optimizer=None; self.runs=[]; self.result=None; self.comparison=None
        self.current_execution=0; self.message=""; self._phase=""; self._started_total=None; self.partial_result=None
    def start(self, request):
        try:
            if isinstance(request,ExecutionConfig):
                algorithm=request.algorithm[0] if isinstance(request.algorithm,tuple) else request.algorithm
                mode=AlgorithmMode.COMPARE if algorithm=="Comparar ambos" else (AlgorithmMode.HEURISTIC if algorithm.startswith("Vizinho") else AlgorithmMode.GENETIC)
                request=ExperimentRequest(ProblemType.TSP,mode,replace(request,algorithm=algorithm),self._legacy_cities)
            request.validate(); self.clear(); self.request=request; self.config=request.execution_config; self.state=ProcessingState.RUNNING; self._started_total=time.perf_counter()
            self._phase="genetic" if request.algorithm_mode in (AlgorithmMode.GENETIC,AlgorithmMode.COMPARE) else "heuristic"; self._start_run()
        except Exception as exc: self.fail(exc)
    def _start_run(self):
        mode=AlgorithmMode.GENETIC if self._phase=="genetic" else AlgorithmMode.HEURISTIC; self.current_execution+=1
        seed=None if mode is AlgorithmMode.HEURISTIC else ((self.config.random_seed+self.current_execution-1) if self.config.random_seed is not None else secrets.randbits(32))
        cfg=replace(self.config,random_seed=seed); self.optimizer=create_optimizer(self.request.problem_type,mode)
        data=self.request.tsp_cities if self.request.problem_type is ProblemType.TSP else self.request.hospital_scenario
        self.optimizer.initialize(data,cfg); self._seed=seed; self._started=time.perf_counter(); log.info("Execução %s %s semente=%s",self.request.problem_type.value,mode.value,seed)
    def _hospital_run(self,partial=False):
        solution=self.optimizer.get_best_solution(); metrics=()
        if solution is None:return None
        metrics=tuple(HospitalGenerationMetric(i+1,cost,solution.total_distance_km,solution.total_delay_minutes,len(solution.unassigned_deliveries),sum(bool(r.stops) for r in solution.routes)) for i,cost in enumerate(self.optimizer.get_history()))
        return HospitalRunResult(self.current_execution,self._seed,tuple(self.optimizer.get_best_route()),solution,metrics,time.perf_counter()-self._started,partial)
    def _consolidate_hospital(self,algorithm,runs):
        best=min(runs,key=lambda x:x.solution.objective_cost); values=[r.solution.objective_cost for r in runs]
        return HospitalExperimentResult(algorithm,tuple(runs),best,statistics.fmean(values),max(values),statistics.stdev(values) if len(values)>1 else 0.,statistics.fmean(r.elapsed_seconds for r in runs))
    def step(self,amount=1):
        if self.state is not ProcessingState.RUNNING:return
        try:
            for _ in range(amount):
                self.optimizer.step()
                if not self.optimizer.is_finished():continue
                if self.request.problem_type is ProblemType.HOSPITAL: run=self._hospital_run()
                else: run=RunResult(self.current_execution,self.optimizer.get_best_route(),self.optimizer.get_best_fitness(),self.optimizer.get_history(),time.perf_counter()-self._started,self._seed)
                self.runs.append(run)
                if self._phase=="genetic" and self.current_execution<self.config.executions: self._start_run(); continue
                completed=self._consolidate_hospital(self._phase,self.runs) if self.request.problem_type is ProblemType.HOSPITAL else consolidate("Algoritmo Genético" if self._phase=="genetic" else "Vizinho Mais Próximo",self.runs)
                if self.request.algorithm_mode is AlgorithmMode.COMPARE and self._phase=="genetic": self._genetic_result=completed; self.runs=[]; self.current_execution=0; self._phase="heuristic"; self._start_run(); continue
                if self.request.algorithm_mode is AlgorithmMode.COMPARE:
                    if self.request.problem_type is ProblemType.HOSPITAL:
                        g,h=self._genetic_result,completed; gs,hs=g.best_run.solution,h.best_run.solution
                        pct=improvement_percentage(gs.objective_cost,hs.objective_cost); self.comparison=HospitalComparisonResult(g,h,abs(hs.objective_cost-gs.objective_cost),pct,abs(hs.total_distance_km-gs.total_distance_km),abs(hs.total_delay_minutes-gs.total_delay_minutes),len(hs.unassigned_deliveries)-len(gs.unassigned_deliveries))
                    else:
                        diff=abs(completed.best_run.best_fitness-self._genetic_result.best_run.best_fitness); pct=improvement_percentage(self._genetic_result.best_run.best_fitness,completed.best_run.best_fitness); self.comparison=ComparisonResult(self._genetic_result,completed,diff,pct)
                    self.result=self._genetic_result
                else:self.result=completed
                if self._phase=="heuristic" and self.config.executions>1:self.message="A heurística determinística foi executada uma vez."
                self.state=ProcessingState.FINISHED; break
        except Exception as exc:self.fail(exc)
    def pause(self):
        if self.state is ProcessingState.RUNNING:self.state=ProcessingState.PAUSED
    def resume(self):
        if self.state is ProcessingState.PAUSED:self.state=ProcessingState.RUNNING
    def cancel(self):
        if self.state in (ProcessingState.RUNNING,ProcessingState.PAUSED):
            if self.request and self.request.problem_type is ProblemType.HOSPITAL:self.partial_result=self._hospital_run(True)
            self.state=ProcessingState.CANCELLED; log.info("Execução cancelada; parcial=%s",bool(self.partial_result))
    def fail(self,error): self.state=ProcessingState.ERROR; self.message=str(error); log.error("Falha: %s\n%s",error,traceback.format_exc())
    def get_snapshot(self):
        generation=getattr(self.optimizer,"generation",1 if self.optimizer and self.optimizer.is_finished() else 0); best=self.best_fitness
        return RunnerSnapshot(self.state,self.request.problem_type if self.request else None,self.request.algorithm_mode if self.request else None,self._phase,self.current_execution,(self.config.executions if self._phase=="genetic" and self.config else 1),generation,self.config.generations if self.config else 0,None if best==float("inf") else best,None if not self.result else (self.result.best_run.solution.objective_cost if hasattr(self.result.best_run,"solution") else self.result.best_run.best_fitness),(time.perf_counter()-self._started_total if self._started_total else 0.),self.message,self.partial_result,self.comparison or self.result)
    @property
    def best_route(self):return self.optimizer.get_best_route() if self.optimizer else []
    @property
    def best_fitness(self):return self.optimizer.get_best_fitness() if self.optimizer else float("inf")
    @property
    def history(self):return self.optimizer.get_history() if self.optimizer else []
